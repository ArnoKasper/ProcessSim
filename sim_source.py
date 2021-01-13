"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""

from flow_item import Order
import numpy as np
import pandas as pd
import random


class Source(object):
    def __init__(self, simulation, stationary=True):
        """
        :param simulation:
        :param stationary:
        """
        self.sim = simulation
        self.stationary = stationary
        self.random_generator = random.Random()
        self.random_generator.seed(999999)
        self.mean_time_between_arrivals = self.sim.model_panel.MEAN_TIME_BETWEEN_ARRIVAL

        if not self.stationary:
            self.non_stationary = NonStationaryControl(simulation=self.sim, source=self)

            # activate non-stationary manager
            self.non_stationary_manager = self.non_stationary.non_stationary_manager()

    def generate_random_arrival_exp(self):
        i = 1
        while True:
            # count input
            self.sim.data_exp.order_input_counter += 1

            # create an order object and give it a name
            order = Order(simulation=self.sim)
            order.entry_time = self.sim.env.now
            order.name = ('Order%07d' % i)
            order.identifier = i

            # release control
            if self.sim.policy_panel.release_control:
                order.process = self.sim.env.process(self.sim.release_control.order_pool(order=order))
            else:
                order.process = self.sim.process.put_in_queue(order=order)

            # next inter arrival time
            if not self.stationary:
                inter_arrival_time = \
                    self.sim.random_generator.expovariate(1 / self.non_stationary.current_mean_between_arrival)
            else:
                inter_arrival_time = self.random_generator.expovariate(1 / self.mean_time_between_arrivals)

            yield self.sim.env.timeout(inter_arrival_time)
            i += 1
            if self.sim.env.now >= (self.sim.model_panel.WARM_UP_PERIOD + self.sim.model_panel.RUN_TIME) \
                    * self.sim.model_panel.NUMBER_OF_RUNS:
                break


class NonStationaryControl(object):
    def __init__(self, simulation, source):
        """
        initialize non-stationary control variables
        :param simulation:
        :param source:
        """
        # general params
        self.sim = simulation
        self.source = source
        self.random_generator = random.Random()
        self.random_generator.seed(999999)

        self.plot_trajectory = False
        self.print_info = False
        self.force_run_time = True
        self.save_non_stationary_database = False

        # stationary params
        self.current_utilization = self.sim.model_panel.AIMED_UTILIZATION
        self.current_cv = 1
        self.current_mean_between_arrival = self.source.mean_time_between_arrivals
        self.current_pattern = "warm_up"

        # trail patterns available
        """
        -   stationary      (stationary period)
        -   systematic      (increase of CV)
        -   stratification  (decrease of CV)
        -   cyclic          (longer periods of up and down shifts of CV)
        -   upward_trend    (monotonic increase in utilization)
        -   downward_trend  (monotonic decrease in utilization)
        -   upward_shift    (sudden increase in utilization)
        -   downward_shift  (sudden decrease in utilization)
        """
        # initiate hard coded pattern
        pattern_sequence, total_time = self.hard_code_pattern()
        self.pattern_sequence = pattern_sequence
        self.total_time = total_time
        if self.force_run_time:
            self.sim.model_panel.RUN_TIME = self.total_time

        # print plot
        if self.plot_trajectory:
            self.plot_system(show_emperical_trajectory=False, save=True)
        # save database
        if self.save_non_stationary_database:
            self.save_non_stationary_list()

    # non stationary pattern -------------------------------------------------------------------------------------------
    def hard_code_pattern(self):
        pattern_sequence = list()
        time = 1000
        total_time = 0
        # 1: stationary period
        pattern_sequence.append(self.pattern_stationary(time=time, utilization=0.9, cv=1))
        total_time += time
        # 2: increase utilization period
        pattern_sequence.append(self.pattern_upward_or_downward_trend(time=1500,
                                                                      utilization_from=0.9,
                                                                      utilization_till=0.95,
                                                                      interval=100,
                                                                      cv=1)
                                )
        total_time += 1500
        # 3: shift utilization down
        pattern_sequence.append(self.pattern_upward_or_downward_shift(time=5000,
                                                                      utilization_from=0.95,
                                                                      utilization_till=0.85,
                                                                      interval=5000 / 2,
                                                                      cv=1)
                                )
        total_time += 5000
        # 2: decrease utilization period
        pattern_sequence.append(self.pattern_upward_or_downward_trend(time=1500,
                                                                      utilization_from=0.85,
                                                                      utilization_till=0.9,
                                                                      interval=100,
                                                                      cv=1)
                                )
        total_time += 1500
        # 3: stationary period
        pattern_sequence.append(self.pattern_stationary(time=time, utilization=0.9, cv=1))
        total_time += time
        return pattern_sequence, total_time

    # non stationary control -------------------------------------------------------------------------------------------
    def non_stationary_manager(self):
        # import lists
        time_list, utilization_list, cv_list, pattern_name_list = \
            self.time_pattern_list(patterns_sequence=self.pattern_sequence)

        # import params
        number_of_patterns = len(time_list) - 1
        index = 0
        run_time = 0
        previous_time = 0
        run_number = 1

        # loop to manage the run dynamics
        while True:
            # get step params
            time = time_list[index] + run_time - previous_time
            previous_time = time_list[index] + run_time
            self.current_cv = cv_list[index]
            self.current_pattern = pattern_name_list[index]
            index += 1

            # change mean time between arrival
            if self.current_utilization != utilization_list[index]:
                self.current_utilization = utilization_list[index]
                self.current_mean_between_arrival = \
                    self.sim.general_functions.arrival_time_caluclation(
                        wc_and_flow_config=self.sim.model_panel.WC_AND_FLOW_CONFIGURATION,
                        manufacturing_floor_layout=self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT,
                        aimed_utilization=self.current_utilization,
                        mean_process_time=self.sim.model_panel.MEAN_PROCESS_TIME,
                        number_of_machines=self.sim.model_panel.NUMBER_OF_MACHINES,
                        cv=self.current_cv)

                if self.print_info:
                    print(f"\n\tMean time between arrival: {self.current_mean_between_arrival}\n"
                          f"\tAimed utilization {self.current_utilization}\n"
                          f"\tCurrent pattern {self.current_pattern}\n")

            # yield until the next change
            yield self.sim.env.timeout(time)

            # break loop if all patterns are visited
            if number_of_patterns == index:
                index = 0
                run_time += self.sim.model_panel.RUN_TIME
                previous_time = int(self.sim.env.now) - self.sim.model_panel.WARM_UP_PERIOD * run_number
                run_number += 1

                if self.print_info:
                    print(f"reset experiment trajectory {self.sim.env.now}")
        return

    # pattern list translate -------------------------------------------------------------------------------------------
    def time_pattern_list(self, patterns_sequence, cv=1):
        """
        Method that makes a list with the pattern of the non-stationary system
        :param patterns_sequence:
        :param cv:
        :return: time_list, utilization_list, cv_list, pattern_name_list
        """
        # initialze lists
        time_list = list()
        utilization_list = list()
        cv_list = list()
        pattern_name_list = list()

        # loop params
        time = self.sim.model_panel.WARM_UP_PERIOD
        utilization = self.current_utilization
        cv = cv

        # loop for each pattern
        """
        - 0: pattern name              <string>
        - 1: time span:                <float>
        - 2: utilization [from, to]    <list, int>
        - 3: utilization change by     <int>
        - 4: cv [from, to]             <list, int>
        - 5: cv change by              <float>
        - 6: interval                  <int>                 
        """
        for i, pattern_list in enumerate(patterns_sequence):
            # check if utilization will change
            if pattern_list[3] != 'na':
                if pattern_list[0][-5:-1] == "shif":
                    time_shift = [time, time + pattern_list[6] - 0.000001,
                                  time + pattern_list[6],
                                  time + pattern_list[1]
                                  ]
                    time += pattern_list[1]
                    time_list.extend(time_shift)
                    utilization_shift = [utilization,
                                         utilization,
                                         (utilization - pattern_list[3]),
                                         (utilization - pattern_list[3])
                                         ]
                    utilization_list.extend(utilization_shift)
                    utilization = utilization - pattern_list[3]
                    cv_list_shift = [pattern_list[4][0]] * 4
                    cv_list.extend(cv_list_shift)
                    utilization_shift = [pattern_list[0]] * 4
                    pattern_name_list.extend(utilization_shift)

                elif pattern_list[0][-5:-1] == "tren":
                    number_of_changes = int(pattern_list[1] / pattern_list[6])
                    for j in range(0, number_of_changes):
                        time_list.append(time)
                        time += pattern_list[6]
                        utilization_list.append(utilization)
                        utilization += pattern_list[3]
                        cv_list.append(pattern_list[4][0])
                        pattern_name_list.append(pattern_list[0])

            # check if cv will change
            elif pattern_list[5] != 'na':
                number_of_changes = int(pattern_list[1] / pattern_list[6])
                for j in range(0, number_of_changes):
                    time_list.append(time)
                    time += pattern_list[6]
                    utilization_list.append(pattern_list[2][0])
                    cv_list.append(cv)
                    cv += pattern_list[5]
                    pattern_name_list.append(pattern_list[0])
            # stationary period
            else:
                time_list.append(time)
                time += pattern_list[1]
                utilization_list.append(pattern_list[2][0])
                cv_list.append(pattern_list[4][0])
                pattern_name_list.append(pattern_list[0])
        return time_list, utilization_list, cv_list, pattern_name_list

    # pattern list -----------------------------------------------------------------------------------------------------
    def pattern_stationary(self, time, utilization, cv):
        """
        returns list with the pattern of the stationary events
        :param time:
        :param utilization:
        :param cv:
        :return: return_list

        Key for the list
        - 0: pattern name              <string>
        - 1: time span:                <float>
        - 2: utilization [from, to]    <list, int>
        - 3: utilization change by     <int>
        - 4: cv [from, to]             <list, int>
        - 5: cv change by              <float>
        - 6: interval                  <int>
        """
        # setup params
        return_list = list()
        # pattern name
        return_list.append("stationary")
        # time span
        return_list.append(time)
        # utilization
        util_list = [utilization, utilization]
        return_list.append(util_list)
        # utilization change by
        return_list.append('na')
        # cv list
        cv_list = [cv, cv]
        return_list.append(cv_list)
        # cv change by
        return_list.append('na')
        # interval
        return_list.append(time)
        return return_list

    def pattern_systematic_or_stratification(self, time, utilization, cv_from, cv_to, interval):
        """
        method that makes an systematic or stratification pattern
        :param time:
        :param utilization:
        :param cv_from:
        :param cv_to:
        :param interval:
        :return:
        """
        if time < interval:
            print("interval is larger than time, default assumption interval = time / 10")
            interval = time / 10
        # setup params
        return_list = list()
        # pattern name
        if cv_from > cv_to:
            return_list.append("stratification")
        else:
            return_list.append("systematic")
        # time span
        return_list.append(time)
        # utilization
        util_list = [utilization, utilization]
        return_list.append(util_list)
        # utilization change by
        return_list.append('na')
        # cv list
        cv_list = [cv_from, cv_from]
        return_list.append(cv_list)
        # cv change by
        cv_delta = (cv_to - cv_from) / interval
        return_list.append(cv_delta)
        # interval
        return_list.append(interval)
        return return_list

    def pattern_cyclic(self, time, utilization, cv_min, cv_max, interval):
        """
        method that makes an cyclic pattern
        :param time:
        :param utilization:
        :param cv_min:
        :param cv_max:
        :param interval:
        :return:
        """
        if time < interval:
            print("interval is larger than time, default assumption interval = time / 10")
            interval = time / 10
        # setup params
        return_list = list()
        # pattern name
        return_list.append("cyclic")
        # time span
        return_list.append(time)
        # utilization
        util_list = [utilization, utilization]
        return_list.append(util_list)
        # utilization change by
        return_list.append('na')
        # cv list
        cv_list = [cv_min, cv_max]
        return_list.append(cv_list)
        # cv change by
        return_list.append('na')
        # interval
        return_list.append(interval)
        return return_list

    def pattern_upward_or_downward_trend(self, time, utilization_from, utilization_till, cv, interval):
        """
        method that makes an upward or downward trend pattern
        :param time:
        :param utilization_from:
        :param utilization_till:
        :param cv:
        :param interval:
        :return:
        """
        if time < interval:
            print("interval is larger than time, default assumption interval = time / 10")
            interval = time / 10
        # setup params
        return_list = list()
        if utilization_from > utilization_till:
            return_list.append("downward_trend")
        else:
            return_list.append("upward_trend")
        # time span
        return_list.append(time)
        # utilization
        util_list = [utilization_from, utilization_till]
        return_list.append(util_list)
        # utilization change by
        utilization_delta = (utilization_till - utilization_from) / (time / interval)
        return_list.append(utilization_delta)
        # cv list
        cv_list = [cv, cv]
        return_list.append(cv_list)
        # cv change by
        return_list.append('na')
        # interval
        return_list.append(interval)
        return return_list

    def pattern_upward_or_downward_shift(self, time, utilization_from, utilization_till, cv, interval):
        """
        method that makes an upward or downward shift pattern
        :param time:
        :param utilization_from:
        :param utilization_till:
        :param cv:
        :param interval:
        :return:
        """
        if time < interval:
            print("interval is larger than time, default assumption interval = time / 10")
            interval = time / 10
        # setup params
        return_list = list()
        if utilization_from > utilization_till:
            return_list.append("downward_shift")
        else:
            return_list.append("upward_shift")
        # time span
        return_list.append(time)
        # utilization
        util_list = [utilization_from, utilization_till]
        return_list.append(util_list)
        # utilization change by
        utilization_delta = (utilization_from - utilization_till)
        return_list.append(utilization_delta)
        # cv list
        cv_list = [cv, cv]
        return_list.append(cv_list)
        # cv change by
        return_list.append('na')
        # interval
        interval = 0.5 * time
        return_list.append(interval)
        return return_list

    # utilities --------------------------------------------------------------------------------------------------------
    def plot_system(self, show_emperical_trajectory=True, save=False):
        """
        method that plots the non-stationary patern
        :param show_emperical_trajectory:
        :param save:
        :return:
        """
        import matplotlib.pyplot as plt

        # get data
        time_list, utilization_list, cv_list, pattern_name_list = self.time_pattern_list(
            patterns_sequence=self.pattern_sequence)
        # put data in dataframe
        if show_emperical_trajectory:
            # get empirical values
            empirical_list, new_time_list, new_utilization_list = \
                self.pseudo_random_generator(time_list=time_list, utilization_list=utilization_list)

            # moving average of utilization
            empirical_list = self.moving_average(mva_list=empirical_list, n=500)

            df = pd.DataFrame({'x': new_time_list,
                               'y_1': new_utilization_list,
                               "empirical": empirical_list})
        else:
            df = pd.DataFrame({'x': time_list, 'y_1': utilization_list})

        if show_emperical_trajectory:
            # add to the plot
            plt.plot('x', 'empirical', data=df, linestyle='-', color="blue", linewidth=1, alpha=0.4)
        # finnish the plot
        # Make a plot to visualize the results
        plt.plot('x', 'y_1', data=df, linestyle='-', color="black", linewidth=2)
        plt.title("Non Stationary Trajectory")
        plt.xlabel("time")
        plt.ylabel("Utilization")
        if save:
            plt.savefig('non_stationary_trajectory.png', dpi=96)
        # manipulate
        plt.gca().set_yticklabels(['{:.0f}%'.format(x * 100) for x in plt.gca().get_yticks()])
        plt.show()
        return

    def pseudo_random_generator(self, time_list, utilization_list, start_time=0):
        """

        :param time_list:
        :param utilization_list:
        :param start_time:
        :return:
        """
        # setup params
        index = 0
        loop_time = start_time
        current_mean_between_arrival = self.current_mean_between_arrival

        # looping lists
        emperical_list = list()
        new_time_list = list()
        new_utilization_list = list()

        # loop
        while True:
            inter_arrival_time = self.random_generator.expovariate(1 / current_mean_between_arrival)
            utilization = 1 - (inter_arrival_time / self.sim.model_panel.MEAN_PROCESS_TIME)
            # utilization += 1

            if loop_time >= time_list[index]:
                # control if loop needs to be broken
                if loop_time > time_list[len(time_list) - 1] + time_list[0]:
                    break
                elif loop_time > time_list[len(time_list) - 1]:
                    current_utilization = utilization_list[index - 1]
                else:
                    # correct index
                    index += 1
                    # change mean time between arrival
                    current_utilization = utilization_list[index]

                current_mean_between_arrival = \
                    self.sim.general_functions.arrival_time_caluclation(
                        wc_and_flow_config=self.sim.model_panel.WC_AND_FLOW_CONFIGURATION,
                        manufacturing_floor_layout=self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT,
                        aimed_utilization=current_utilization,
                        mean_process_time=self.sim.model_panel.MEAN_PROCESS_TIME,
                        number_of_machines=self.sim.model_panel.NUMBER_OF_MACHINES,
                        cv=self.current_cv)

                # update the time
                loop_time += inter_arrival_time
            else:
                # update the time
                loop_time += inter_arrival_time

            # update lists
            emperical_list.append(utilization)
            new_time_list.append(loop_time)
            new_utilization_list.append(utilization_list[index])

        return emperical_list, new_time_list, new_utilization_list

    def moving_average(self, mva_list, n):
        """

        :param mva_list:
        :param n:
        :return:
        """
        cumsum, moving_aves = [0], []

        for i, x in enumerate(mva_list, 1):
            cumsum.append(cumsum[i - 1] + x)
            if i >= n:
                moving_ave = (cumsum[i] - cumsum[i - n]) / n
                # can do stuff with moving_ave here
                moving_aves.append(moving_ave)
            else:
                moving_aves.append(np.nan)

        return moving_aves

    def save_non_stationary_list(self, file_pattern=".csv"):
        """
        save the pattern list of the non-stationary events
        :param file_pattern:
        :return:
        """
        # import libraries
        import exp_manager as exp_manager
        # import lists
        time_list, utilization_list, cv_list, pattern_name_list = self.time_pattern_list(
            patterns_sequence=self.pattern_sequence)
        # put into a dataframe
        df = pd.DataFrame({'time': time_list,
                           'utilization': utilization_list,
                           "pattern name": pattern_name_list})
        # get path
        path = exp_manager.Experiment_Manager.get_directory("spam")

        # make file name
        path = path + "non_stationary_list" + file_pattern

        # save database
        exp_manager.Experiment_Manager.save_database_csv(self="spam", file=path, database=df)
        # print info
        print("#### non stationary control database saved ####")
        return
