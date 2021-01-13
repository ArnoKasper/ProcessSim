"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""
import statistics
import numpy as np
import pandas as pd

class DataStorageRun(object):
    def __init__(self, sim):
        self.sim = sim

        # General data
        self.Run = list()
        self.Number = 0  # Number of Orders processed
        self.StationNumber = [0] * len(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT)
        self.CalculateUtiliz = 0  # Utilization machine

        # Throughput Time measures
        self.GrossThroughputTime = list()  # Record Throughput from entry to finish
        self.pooltime = list()  # Record Throughput from entry to release
        self.ThroughputTime = list()  # Record Throughput from release to finish

        # work centre measures
        self.StationGrossThroughputTime = dict()
        self.Stationpooltime = dict()
        self.StationThroughputTime = dict()
        for i, WC in enumerate(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT):
            self.StationGrossThroughputTime[WC] = list()
            self.Stationpooltime[WC] = list()
            self.StationThroughputTime[WC] = list()

        # Tardiness measures
        self.Tardiness = list()  # Records the tardiness of all orders
        self.CumTardiness = 0
        self.NumberTardy = 0  # Counts the tardy orders
        self.Lateness = list()

        if self.sim.model_panel.CollectPeriodicData:
            self.PeriodicData = [list()] * len(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT)

        self.ContLUMSCORCounter = 0
        self.QSCounter = 0
        self.order_input_counter = 0
        self.order_output_counter = 0


#### Collection variables of each experiment ---------------------------------------------------------------------------
class DataStorageExp(object):
    def __init__(self, sim):
        self.sim = sim

        # general info
        self.order_input_counter = 0
        self.order_output_counter = 0

        if self.sim.model_panel.CollectBasicData:
            self.Dat_exp_run = list()
            self.Dat_exp_number_orders = list()
            self.Dat_expUtilization = list()
            self.Dat_exp_GrossThroughputTime_mean = list()
            self.Dat_exp_pooltime_mean = list()
            self.Dat_exp_ThroughputTime_mean = list()
            self.Dat_exp_GrossThroughputTime_var = list()
            self.Dat_exp_pooltime_var = list()
            self.Dat_exp_ThroughputTime_var = list()
            self.Dat_exp_Tardiness_mean = list()
            self.Dat_exp_Lateness_mean = list()
            self.Dat_exp_percentageTardy = list()
            self.Dat_exp_Tardiness_var = list()
            self.Dat_exp_Lateness_var = list()
            self.Dat_exp_ConLUMSCOR = list()
            self.Dat_exp_QSCounter = list()

            if self.sim.model_panel.CollectStationData:
                self.Run_StationGrossThroughputTime_mean_WC = dict()
                self.Run_Stationpooltime_mean_WC = dict()
                self.Run_StationThroughputTime_mean_WC = dict()
                self.Run_StationGrossThroughputTime_var_WC = dict()
                self.Run_StationThroughputTime_var_WC = dict()

                for i, WC in enumerate(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT):
                    self.Run_StationGrossThroughputTime_mean_WC[WC] = list()
                    self.Run_Stationpooltime_mean_WC[WC] = list()
                    self.Run_StationThroughputTime_mean_WC[WC] = list()
                    self.Run_StationGrossThroughputTime_var_WC[WC] = list()
                    self.Run_StationThroughputTime_var_WC[WC] = list()


        if self.sim.model_panel.CollectFlowData:
            self.Dat_exp_flow_WC = list()
            self.Dat_exp_flow_MC = list()
            for i in range(0, 8):
                list_wc = list()

                for j in range(0, 6):
                    list_wc.append(0)

                self.Dat_exp_flow_WC.append(list_wc)

        if self.sim.model_panel.CollectMachineData:
            self.MachineData = list()
            self.list_tracking = [0] * self.sim.model_panel.NUMBER_OF_MACHINES * len(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT)
            self.previous_time = 0

        if self.sim.model_panel.CollectPeriodicData:
            self.PeriodicData = [[]] * len(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT)

        if self.sim.model_panel.CollectDiscreteData:
            self.discrete_data = pd.DataFrame({"value": [*range(-50, 301)]})
            self.discrete_data["count"] = 0

        if self.sim.model_panel.CollectOrderData:
            self.variable_1 = list()
            self.variable_2 = list()
            self.variable_3 = list()


class DataCollection(object):
    """
    This class contains all the methods associated with data collection.
    Depending on the settings the method will be used for data collection.
    1. Activated by the run_manager()
        - basic data collection
        - Periodic data collection
        - Order data collection
    2. Activated by the manufacturing_process()
        - Flow data
        - Machine data
    3. Method to empty the sim.model_pannel
    """
    def __init__(self, simulation):
        self.sim = simulation

    def basic_data_storage(self):
        # declare params
        Run_StationGrossThroughputTime_mean = dict()
        Run_Stationpooltime_mean = dict()
        Run_StationThroughputTime_mean = dict()
        Run_StationGrossThroughputTime_var = dict()
        Run_Stationpooltime_var = dict()
        Run_StationThroughputTime_var = dict()

        # Results are stored for this run-------------------------------------------------------------------------------
        # General results
        Run_experiment_run = (int(self.sim.env.now / (self.sim.model_panel.WARM_UP_PERIOD + self.sim.model_panel.RUN_TIME)))
        Run_number_orders = self.sim.data_run.Number

        number_of_machines_in_process = (self.sim.model_panel.NUMBER_OF_MACHINES * len(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT))
        Run_Utilization = ((self.sim.data_run.CalculateUtiliz * 100 / number_of_machines_in_process) / self.sim.model_panel.RUN_TIME)

        # Throughput Time measures (GENERAL)
        # Means
        Run_GrossThroughputTime_mean = statistics.mean(self.sim.data_run.GrossThroughputTime)
        Run_pooltime_mean = statistics.mean(self.sim.data_run.pooltime)
        Run_ThroughputTime_mean = statistics.mean(self.sim.data_run.ThroughputTime)
        # Variance
        Run_GrossThroughputTime_var = statistics.variance(self.sim.data_run.GrossThroughputTime)
        Run_pooltime_var = statistics.variance(self.sim.data_run.pooltime)
        Run_ThroughputTime_var = statistics.variance(self.sim.data_run.ThroughputTime)

        # Throughput Time measures (STATION)
        if self.sim.model_panel.CollectStationData:
            for i, WC in enumerate(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT):
                Run_StationGrossThroughputTime_mean[WC] = list()
                Run_Stationpooltime_mean[WC] = list()
                Run_StationThroughputTime_mean[WC] = list()
                Run_StationGrossThroughputTime_var[WC] = list()
                Run_Stationpooltime_var[WC] = list()
                Run_StationThroughputTime_var[WC] = list()
                # Means
                Run_StationGrossThroughputTime_mean[WC] = statistics.mean(self.sim.data_run.StationGrossThroughputTime[WC])
                Run_Stationpooltime_mean[WC] = statistics.mean(self.sim.data_run.Stationpooltime[WC])
                Run_StationThroughputTime_mean[WC] = statistics.mean(self.sim.data_run.StationThroughputTime[WC])
                # Variance
                Run_StationGrossThroughputTime_var[WC] = statistics.variance(self.sim.data_run.StationGrossThroughputTime[WC])
                Run_Stationpooltime_var[WC] = statistics.variance(self.sim.data_run.Stationpooltime[WC])
                Run_StationThroughputTime_var[WC] = statistics.variance(self.sim.data_run.StationThroughputTime[WC])

        # Tardiness measures
        Run_percentageTardy = self.sim.data_run.NumberTardy / self.sim.data_run.Number
        # Mean
        Run_Tardiness_mean = statistics.mean(self.sim.data_run.Tardiness)
        Run_Lateness_mean = statistics.mean(self.sim.data_run.Lateness)
        # Variance
        Run_Tardiness_var = statistics.variance(self.sim.data_run.Tardiness)
        Run_Lateness_var = statistics.variance(self.sim.data_run.Lateness)

        # Safe experimental data in database------------------------------------------------------------------------
        self.sim.data_exp.Dat_exp_run.append(Run_experiment_run)
        self.sim.data_exp.Dat_exp_number_orders.append(Run_number_orders)
        self.sim.data_exp.Dat_expUtilization.append(Run_Utilization)
        self.sim.data_exp.Dat_exp_GrossThroughputTime_mean.append(Run_GrossThroughputTime_mean)
        self.sim.data_exp.Dat_exp_pooltime_mean.append(Run_pooltime_mean)
        self.sim.data_exp.Dat_exp_ThroughputTime_mean.append(Run_ThroughputTime_mean)
        self.sim.data_exp.Dat_exp_GrossThroughputTime_var.append(Run_GrossThroughputTime_var)
        self.sim.data_exp.Dat_exp_pooltime_var.append(Run_pooltime_var)
        self.sim.data_exp.Dat_exp_ThroughputTime_var.append(Run_ThroughputTime_var)
        self.sim.data_exp.Dat_exp_Tardiness_mean.append(Run_Tardiness_mean)
        self.sim.data_exp.Dat_exp_Lateness_mean.append(Run_Lateness_mean)
        self.sim.data_exp.Dat_exp_percentageTardy.append(Run_percentageTardy)
        self.sim.data_exp.Dat_exp_Tardiness_var.append(Run_Tardiness_var)
        self.sim.data_exp.Dat_exp_Lateness_var.append(Run_Lateness_var)
        self.sim.data_exp.Dat_exp_ConLUMSCOR.append(self.sim.data_run.ContLUMSCORCounter)
        self.sim.data_exp.Dat_exp_QSCounter.append(self.sim.data_run.QSCounter)

        if self.sim.model_panel.CollectStationData:
            for i, WC in enumerate(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT):
                self.sim.data_exp.Run_StationGrossThroughputTime_mean_WC[WC].append(Run_StationGrossThroughputTime_mean[WC])
                self.sim.data_exp.Run_Stationpooltime_mean_WC[WC].append(Run_Stationpooltime_mean[WC])
                self.sim.data_exp.Run_StationThroughputTime_mean_WC[WC].append(Run_StationThroughputTime_mean[WC])
                self.sim.data_exp.Run_StationGrossThroughputTime_var_WC[WC].append(Run_StationGrossThroughputTime_var[WC])
                self.sim.data_exp.Run_StationThroughputTime_var_WC[WC].append(Run_StationThroughputTime_var[WC])
        return

    def periodic_data_collection(self, sim):
        while True:
            # yield a timeout every periodic time interval
            yield sim.env.timeout(sim.model_panel.CollectPeriodicData_time_interval)
            i = 0
            for WC in sim.model_panel.MANUFACTURING_FLOOR_LAYOUT:
                workload = sim.model_panel.RELEASED[WC] - sim.model_panel.PROCESSED[WC]
                sim.model_panel.PeriodicData[i].append(workload)
                i += 1
            if sim.env.now >= (sim.model_panel.WARM_UP_PERIOD + sim.model_panel.RUN_TIME) * sim.model_panel.NUMBER_OF_RUNS:
                break

    def flow_data_collection(self, order, sim):
        for i, WC in enumerate(order.routing_sequence_data):
            # Get the WC string from the routing sequence
            string_from_wc = order.routing_sequence_data[i]
            string_to_wc = order.routing_sequence_data[i + 1]

            # Remove WC and transform the WC number to an integer (- 1 to correct for index starting at 0)
            from_wc = int(string_from_wc[2]) - 1
            to_wc = int(string_to_wc[2]) - 1

            # Add flow information to the data collect list
            sim.data_exp.Dat_exp_flow_WC[from_wc][to_wc] += 1

        for j in range(0, (len(order.routing_sequence_data))):
            string_from_wc = order.routing_sequence_data[j]
            from_wc = int(string_from_wc[2]) - 1

            # Add machine flow information
            if order.machine_route[string_from_wc] == 0:
                sim.data_exp.Dat_exp_flow_WC[6][from_wc] += 1

            elif order.machine_route[string_from_wc] == 1:
                sim.data_exp.Dat_exp_flow_WC[7][from_wc] += 1
        return

    def machine_data_collection(self, order):
        sim.data_exp.MachineData.append(self.sim.data_exp.list_tracking)
        sim.data_exp.list_tracking = [0] * self.sim.model_panel.NUMBER_OF_MACHINES * len(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT)

        for a in range(0, (len(order.routing_sequence_data))):
            string_WC = order.routing_sequence_data[a]
            WC = int(string_WC[2]) - 1

            # Track machine data
            # index = a * 2

            # Track Work Centre data
            index = a

            # Add machine flow information
            if order.machine_route[string_WC] == 0:
                DataStorageExp.list_tracking[index] += order.WCNumber

            elif order.machine_route[string_WC] == 1:
                # Data_Storage_Exp.list_tracking[index + 1] += self.WCNumber
                DataStorageExp.list_tracking[index] += order.WCNumber
        return

    def station_data_collection(self, order):
        for i, WorkCenter in enumerate(order.routing_sequence_data):
            j = int(WorkCenter[2]) - 1
            var_1 = order.queue_time[WorkCenter]
            var_2 = order.pool_time
            var_3 = order.process_time[WorkCenter]

            # Throughput Time data collection (STATION)
            self.sim.data_run.StationNumber[j] += 1
            self.sim.data_run.StationGrossThroughputTime[WorkCenter].append(var_1)
            self.sim.data_run.Stationpooltime[WorkCenter].append(var_2)
            self.sim.data_run.StationThroughputTime[WorkCenter].append(var_3)

    def order_data_collection(self, order):
        """
        Key
        - latness order
        - workload
        """
        # impute the time
        self.sim.data_exp.variable_1.append(self.sim.env.now)

        # impute the lateness of each order
        self.sim.data_exp.variable_2.append(order.finishing_time - order.due_date)

        # workload data
        load_direct = 0
        # get load in queue
        for j, WorkCentre in enumerate(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT):
            # the single queue
            if self.sim.model_panel.queue_configuration == "SQ" or self.sim.model_panel.queue_configuration == "SM":
                #for i, order_queue in enumerate(self.sim.model_pannel.ORDER_POOL[WorkCentre].items):
                #    load_direct += order_queue[0].process_time[WorkCentre]
                for i, order_queue in enumerate(self.sim.model_panel.MANUFACTURING_FLOOR[WorkCentre].queue):
                    load_direct += order_queue.self.process_time[WorkCentre]
                 # get the load from work centre user
                if len(self.sim.model_panel.MANUFACTURING_FLOOR[WorkCentre].users) > 0:
                    load_direct += self.sim.model_panel.MANUFACTURING_FLOOR[WorkCentre].users[0].self.process_time[WorkCentre]

            # the multi queue
            elif self.sim.model_panel.queue_configuration == "MQ":
                for _, Machine in enumerate(self.sim.model_panel.MANUFACTURING_FLOOR[WorkCentre]):
                    for _ , order_queue in enumerate(Machine.queue):
                        load_direct += order_queue.self.process_time[WorkCentre]
                    # get the load from work centre user
                    if len(Machine.users) > 0:
                        load_direct += Machine.users[0].self.process_time[WorkCentre]

        # append the list
        if self.sim.model_panel.queue_configuration == "SM":
            load_direct = load_direct * 2

        self.sim.data_exp.variable_3.append(load_direct)

    def order_data_storage(self, sim):
        # Add all general order information to the list
        sim.data_exp.Dat_exp_GrossThroughputTime_mean.extend(sim.data_run.GrossThroughputTime)
        sim.data_exp.Dat_exp_run.extend(sim.data_run.Run)
        sim.data_exp.Dat_exp_pooltime_mean.extend(sim.data_run.pooltime)
        sim.data_exp.Dat_exp_ThroughputTime_mean.extend(sim.data_run.ThroughputTime)
        sim.data_exp.Dat_exp_Tardiness_mean.extend(sim.data_run.Tardiness)
        sim.data_exp.Dat_exp_Lateness_mean.extend(sim.data_run.Lateness)

        # Add all the work centre specific information
        for i, WC in enumerate(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT):
            sim.data_exp.Run_StationGrossThroughputTime_mean_WC1.extend(sim.data_run.StationGrossThroughputTime[i])
            sim.data_exp.Run_Stationpooltime_mean_WC1.extend(sim.data_run.Stationpooltime[i])
            sim.data_exp.Run_StationThroughputTime_mean_WC1.extend(sim.data_run.StationThroughputTime[i])
        return

    def discrete_data_collection(self, sim, value):
        value = int(round(value))
        if value in sim.data_exp.discrete_data.iloc[:, 0].values:
            sim.data_exp.discrete_data.loc[(sim.data_exp.discrete_data["value"] == value), "count"] += 1
        elif value > sim.data_exp.discrete_data.iloc[:, 0].max():
            sim.data_exp.discrete_data.loc[(sim.data_exp.discrete_data["value"] == sim.data_exp.discrete_data.iloc[:, 0].max()), "count"] += 1
        else:
            new_value = {"value": value,
                         "count": 1}
            sim.data_exp.discrete_data = sim.data_exp.discrete_data.append(new_value, ignore_index=True)
        return
