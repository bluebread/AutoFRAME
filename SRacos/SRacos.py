import random
import copy
import operator
import datetime


CONTINUOUS = 0
DISCRETE = 1
CATEGORICAL = 2

_SAMPLE_TIME = 0.0001       # Maximum time for a simple sample


class Optimizer:

    def __init__(self):
        pass

    def opt(self, objective, dimension, budget, k, r, prob, max_coordinates, print_opt=False):
        """
        Optimize the given objective.
        :param objective: A callable function which returns a value.
        :param dimension: A two dimensional list. See README.
        :param budget: Number of samples.
        :param k: Positive region size.
        :param r: Pool size.
        :param prob: Probability to sample from positive region.
        :param max_coordinates: Maximum number of uncertain coordinates.
        :param print_opt: Whether to print opt procedures or not.
        :return: The best solution, a tuple (x, f(x)).
        """
        if k < 1 or k >= r or r > budget:
            raise ValueError
        x_list = self._uniform_sample_without_replicates(dimension, None, r)
        data = self._evaluate_list(x_list, objective)
        positive_data, negative_data = self._selection(data, k)
        best_solution = positive_data[0]
        for t in range(budget - r):
            if random.random() < prob:
                x = self._sample_from_racos_with_retry(dimension, positive_data, negative_data, max_coordinates)
            else:
                x = self._uniform_sample_without_replicates(dimension, positive_data + negative_data, 1)
            y = objective(x)
            inferior = self._replace_wr((x, y), positive_data, 'pos')
            _ = self._replace_wr(inferior, negative_data, 'neg')
            best_solution = positive_data[0]
            if print_opt is True:
                print(best_solution)
        return best_solution

    def _sample_from_racos_with_retry(self, dimension, positive_data, negative_data, max_coordinates):
        x = None
        while x is None:
            x = self._sample_from_racos(dimension, positive_data, negative_data, max_coordinates)
        return x

    def _sample_from_racos(self, dimension, positive_data, negative_data, max_coordinates):
        sample_region = copy.deepcopy(dimension)
        x_positive = positive_data[random.randint(0, len(positive_data) - 1)]
        len_negative = len(negative_data)
        index_set = list(range(len(dimension)))
        types = list(map(lambda x: x[2], dimension))
        while len_negative > 0 and len(index_set) > 0:
            k = index_set[random.randint(0, len(index_set) - 1)]
            x_pos_k = x_positive[0][k]
            # continuous
            if types[k] == CONTINUOUS:
                x_negative = negative_data[random.randint(0, len_negative - 1)]
                x_neg_k = x_negative[0][k]
                if x_pos_k < x_neg_k:
                    r = random.uniform(x_pos_k, x_neg_k)
                    if r < sample_region[k][1]:
                        sample_region[k][1] = r
                        i = 0
                        while i < len_negative:
                            if negative_data[i][0][k] >= r:
                                len_negative -= 1
                                itemp = negative_data[i]
                                negative_data[i] = negative_data[len_negative]
                                negative_data[len_negative] = itemp
                            else:
                                i += 1
                else:
                    r = random.uniform(x_neg_k, x_pos_k)
                    if r > sample_region[k][0]:
                        sample_region[k][0] = r
                        i = 0
                        while i < len_negative:
                            if negative_data[i][0][k] <= r:
                                len_negative -= 1
                                itemp = negative_data[i]
                                negative_data[i] = negative_data[len_negative]
                                negative_data[len_negative] = itemp
                            else:
                                i += 1
            # discrete
            elif types[k] == DISCRETE:
                x_negative = negative_data[random.randint(0, len_negative - 1)]
                x_neg_k = x_negative[0][k]
                if x_pos_k < x_neg_k:
                    # different from continuous version
                    r = random.randint(x_pos_k, x_neg_k - 1)
                    if r < sample_region[k][1]:
                        sample_region[k][1] = r
                        i = 0
                        while i < len_negative:
                            if negative_data[i][0][k] >= r:
                                len_negative -= 1
                                itemp = negative_data[i]
                                negative_data[i] = negative_data[len_negative]
                                negative_data[len_negative] = itemp
                            else:
                                i += 1
                else:
                    r = random.randint(x_neg_k, x_pos_k)
                    if r > sample_region[k][0]:
                        sample_region[k][0] = r
                        i = 0
                        while i < len_negative:
                            if negative_data[i][0][k] <= r:
                                len_negative -= 1
                                itemp = negative_data[i]
                                negative_data[i] = negative_data[len_negative]
                                negative_data[len_negative] = itemp
                            else:
                                i += 1
            elif types[k] == CATEGORICAL:
                delete = 0
                i = 0
                while i < len_negative:
                    if negative_data[i][0][k] != x_pos_k:
                        len_negative -= 1
                        delete += 1
                        itemp = negative_data[i]
                        negative_data[i] = negative_data[len_negative]
                        negative_data[len_negative] = itemp
                    else:
                        i += 1
                if delete != 0:
                    index_set.remove(k)
                    sample_region[k][3] = [x_positive[0][k], ]
            else:
                raise ValueError
        if len(index_set) > max_coordinates:
            indices_list = random.sample(index_set, len(index_set) - max_coordinates)
            for k in indices_list:
                sample_region[k][0] = x_positive[0][k]
                sample_region[k][1] = x_positive[0][k]
                sample_region[k][3] = [x_positive[0][k], ]
                index_set.remove(k)
        x_list = [x[0] for x in positive_data] + [x[0] for x in negative_data]
        return self._uniform_sample_without_replicates(sample_region, x_list, 1)

    @staticmethod
    def _uniform_sample(dimension):
        x = list()
        for i in range(len(dimension)):
            if dimension[i][2] == CONTINUOUS:
                value = random.uniform(dimension[i][0], dimension[i][1])
            elif dimension[i][2] == DISCRETE:
                value = random.randint(dimension[i][0], dimension[i][1])
            elif dimension[i][2] == CATEGORICAL:
                rand_index = random.randint(0, len(dimension[i][3]) - 1)
                value = dimension[i][3][rand_index]
            else:
                raise ValueError
            x.append(value)
        return x

    def _uniform_sample_without_replicates(self, dimension, data, num):
        if data is None:
            data = list()
        if num == 1:
            start_time = datetime.datetime.now()
            x = self._uniform_sample(dimension)
            while any([operator.eq(x, t) for t in data]):
                current_time = datetime.datetime.now()
                if (current_time - start_time).total_seconds() > _SAMPLE_TIME:
                    return None
                x = self._uniform_sample(dimension)
            return x
        elif num > 1:
            x_list = list()
            for i in range(num):
                start_time = datetime.datetime.now()
                x = self._uniform_sample(dimension)
                while any([operator.eq(x, t) for t in data + x_list]):
                    current_time = datetime.datetime.now()
                    if (current_time - start_time).total_seconds() > _SAMPLE_TIME:
                        return None
                    x = self._uniform_sample(dimension)
                x_list.append(x)
            return x_list
        else:
            raise ValueError

    @staticmethod
    def _evaluate_list(x_list, objective):
        return [(x, objective(x)) for x in x_list]

    @staticmethod
    def _selection(data, k):
        new_data = sorted(data, key=lambda item: item[1])
        positive_data = new_data[0: k]
        negative_data = new_data[k: len(new_data)]
        return positive_data, negative_data

    def _replace_wr(self, item, data, iset_type):
        if iset_type == 'pos':
            index = self._binary_search(data, item, 0, len(data) - 1)
            data.insert(index, item)
            worst_ele = data.pop()
            return worst_ele
        elif iset_type == 'neg':
            worst_index = 0
            for i in range(len(data)):
                if data[i][1] > data[worst_index][1]:
                    worst_index = i
            worst_ele = data[worst_index]
            if worst_ele[1] > item[1]:
                data[worst_index] = item
            else:
                worst_ele = item
            return worst_ele

    def _binary_search(self, iset, x, begin, end):
        """
        Find the first element larger than x.
        :param iset: a solution set
        :param x: a Solution object
        :param begin: begin position
        :param end: end position
        :return: the index of the first element larger than x
        """
        x_value = x[1]
        if x_value <= iset[begin][1]:
            return begin
        if x_value >= iset[end][1]:
            return end + 1
        if end == begin + 1:
            return end
        mid = (begin + end) // 2
        if x_value <= iset[mid][1]:
            return self._binary_search(iset, x, begin, mid)
        else:
            return self._binary_search(iset, x, mid, end)

