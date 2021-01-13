"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""
import pandas as pd
import socket
import random
import warnings
import os

import simulation_model as sim


class Experiment_Manager(object):

    # Creat a batch of experiments with a upper an lower limit
    def __init__(self, lower, upper):
        """
        initialize experiments integers
        :param lower: lower boundary of the exp number
        :param upper: upper boundary of the exp number
        """
        self.lower = lower
        self.upper = upper
        self.count_experiment = 0
        self.exp_manager()

    def exp_manager(self):
        """
        define the experiment manager who controls the simulation model
        :return: void
        """
        # use a loop to illiterate multiple experiments from the exp_dat list
        for i in range(self.lower, (self.upper + 1)):
            # activate Simulation experiment method
            self.sim = sim.Simulation_Model(i)

            # finish the experiment by saving the data and move on to the saving function
            exp_variable_list = self.sim.model_panel.project_name

            # save the experiment
            self.saving_exp(exp_variable_list)

    def saving_exp(self, exp_variable_list):
        """
        save all the experiment data versions
        :param exp_variable_list:
        :return:
        """
        ##### Create a database-----------------------------------------------------------------------------------------
        # initialize params
        df_basic = []
        df_wc_flow = []
        df_order = []
        df_machine_data = []
        df_periodic = []

        if self.sim.model_panel.CollectBasicData:
            df_basic = pd.DataFrame([
                self.sim.data_exp.Dat_exp_run,
                self.sim.data_exp.Dat_exp_number_orders,
                self.sim.data_exp.Dat_expUtilization,
                self.sim.data_exp.Dat_exp_GrossThroughputTime_mean,
                self.sim.data_exp.Dat_exp_pooltime_mean,
                self.sim.data_exp.Dat_exp_ThroughputTime_mean,
                self.sim.data_exp.Dat_exp_GrossThroughputTime_var,
                self.sim.data_exp.Dat_exp_pooltime_var,
                self.sim.data_exp.Dat_exp_ThroughputTime_var,
                self.sim.data_exp.Dat_exp_Tardiness_mean,
                self.sim.data_exp.Dat_exp_Lateness_mean,
                self.sim.data_exp.Dat_exp_percentageTardy,
                self.sim.data_exp.Dat_exp_Tardiness_var,
                self.sim.data_exp.Dat_exp_Lateness_var,
                self.sim.data_exp.Dat_exp_ConLUMSCOR,
                self.sim.data_exp.Dat_exp_QSCounter
            ])
            df_basic = df_basic.transpose()
            df_basic.columns = [
                "Dat_exp_run",
                "Dat_exp_number_orders",
                "Dat_expUtilization",
                "Dat_exp_GrossThroughputTime_mean",
                "Dat_exp_pooltime_mean",
                "Dat_exp_ThroughputTime_mean",
                "Dat_exp_GrossThroughputTime_var",
                "Dat_exp_pooltime_var",
                "Dat_exp_ThroughputTime_var",
                "Dat_exp_Tardiness_mean",
                "Dat_exp_Lateness_mean",
                "Dat_exp_percentageTardy",
                "Dat_exp_Tardiness_var",
                "Dat_exp_Lateness_var",
                "Dat_exp_variable_1",
                "Dat_exp_variable_2"]

            if self.sim.model_panel.CollectStationData:
                database_list = list()
                # put in the first variable
                for i, WC in enumerate(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT):
                    df_station = pd.DataFrame([
                        self.sim.data_exp.Run_StationGrossThroughputTime_mean_WC[WC],
                        self.sim.data_exp.Run_Stationpooltime_mean_WC[WC],
                        self.sim.data_exp.Run_StationThroughputTime_mean_WC[WC],
                        self.sim.data_exp.Run_StationGrossThroughputTime_var_WC[WC],
                        self.sim.data_exp.Run_StationThroughputTime_var_WC[WC]
                    ])
                    df_station = df_station.transpose()
                    name_number = i + 1
                    df_station.columns = [
                        "Run_StationQueueTime_mean_WC" + str(name_number),
                        "Run_StationProcTime_mean_WC" + str(name_number),
                        "Run_StationQueueTime_var_WC" + str(name_number),
                        "Run_GrossQueueTime_var_WC" + str(name_number),
                        "Run_StationProcTime_var_WC" + str(name_number),
                    ]
                    # put dataframe list
                    database_list.append(df_station)
                for i, WC in enumerate(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT):
                    df_basic = pd.concat([df_basic, database_list[i]], axis=1)
            else:
                df_basic = df_basic

        if self.sim.model_panel.CollectFlowData:
            df_wc_flow = pd.DataFrame([self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT,
                                       self.sim.data_exp.Dat_exp_flow_WC[0],
                                       self.sim.data_exp.Dat_exp_flow_WC[1],
                                       self.sim.data_exp.Dat_exp_flow_WC[2],
                                       self.sim.data_exp.Dat_exp_flow_WC[3],
                                       self.sim.data_exp.Dat_exp_flow_WC[4],
                                       self.sim.data_exp.Dat_exp_flow_WC[5],
                                       self.sim.data_exp.Dat_exp_flow_WC[6],
                                       self.sim.data_exp.Dat_exp_flow_WC[7]])
            df_wc_flow = df_wc_flow.T
            df_wc_flow.columns = [
                f"Unkown",
                "WC1",
                "WC2",
                "WC3",
                "WC4",
                "WC5",
                "WC6",
                "Machine 1",
                "Machine 2"
            ]
        if self.sim.model_panel.CollectMachineData:
            df_machine_data = pd.DataFrame([self.sim.data_exp.MachineData[0]])
            for i in range(1, len(self.sim.data_exp.MachineData)):
                between = pd.DataFrame([self.sim.data_exp.MachineData[i]])
                df_machine_data = pd.concat([between, df_machine_data], ignore_index=True)

        if self.sim.model_panel.CollectPeriodicData:
            df_periodic = pd.DataFrame([self.sim.data_exp.PeriodicData[0]])
            for i in range(1, len(self.sim.data_exp.PeriodicData)):
                between = pd.DataFrame([self.sim.data_exp.PeriodicData[i]])
                df_periodic = pd.concat([between, df_periodic], ignore_index=True)

            df_periodic = df_periodic.transpose()
            df_periodic.columns = [
                "WC1",
                "WC2",
                "WC3",
                "WC4",
                "WC5",
                "WC6"
            ]
        if self.sim.model_panel.CollectOrderData:
            # create name string
            lenght_name = len(self.sim.data_exp.variable_1)
            name_list = [self.sim.model_panel.experiment_name] * lenght_name
            # put in dataframe
            df_order = pd.DataFrame([
                name_list,
                self.sim.data_exp.variable_1,
                self.sim.data_exp.variable_2,
                self.sim.data_exp.variable_3
            ])
            df_order = df_order.transpose()
            df_order.columns = [
                "name",
                "time",
                "lateness",
                "load"
            ]

        # save file with custom name------------------------------------------------------------------------------------
        # get file directory
        path = self.get_directory()

        # create the experimental name
        exp_name = ""
        for i, string in enumerate(exp_variable_list):
            exp_name = exp_name + str(string) + "_"

        save_list = []

        if self.sim.model_panel.CollectBasicData or self.sim.model_panel.CollectStationData:
            name_and_data_list = []
            save_exp_name = exp_name

            name_and_data_list.append(save_exp_name)
            name_and_data_list.append(df_basic)

            # Put data frame and name in list
            save_list.append(name_and_data_list)

        if self.sim.model_panel.CollectFlowData:
            name_and_data_list = []
            save_exp_name = "FLOW_" + exp_name

            name_and_data_list.append(save_exp_name)
            name_and_data_list.append(df_wc_flow)

            # Put dataframe and name in list
            save_list.append(name_and_data_list)

        if self.sim.model_panel.CollectOrderData:
            name_and_data_list = []
            save_exp_name = "ORDER_" + exp_name

            name_and_data_list.append(save_exp_name)
            name_and_data_list.append(df_order)

            # Put dataframe and name in list
            save_list.append(name_and_data_list)

        if self.sim.model_panel.CollectMachineData:
            name_and_data_list = []
            save_exp_name = "MACHINE_" + exp_name

            name_and_data_list.append(save_exp_name)
            name_and_data_list.append(df_machine_data)
            # Put dataframe and name in list
            save_list.append(name_and_data_list)

        if self.sim.model_panel.CollectPeriodicData:
            name_and_data_list = []
            save_exp_name = "PERIODIC_" + exp_name

            name_and_data_list.append(save_exp_name)
            name_and_data_list.append(df_periodic)

            # Put dataframe and name in list
            save_list.append(name_and_data_list)

        if self.sim.model_panel.CollectDiscreteData:
            name_and_data_list = []
            save_exp_name = "DISCRETE_" + exp_name

            name_and_data_list.append(save_exp_name)
            name_and_data_list.append(self.sim.data_exp.discrete_data)

            # Put dataframe and name in list
            save_list.append(name_and_data_list)

        # save ---------------------------------------------------------------------------------------------------------
        file_version = ".csv"  # ".xlsx"#".csv"#

        for i, name_and_data_list in enumerate(save_list):
            try:
                file = path + name_and_data_list[0] + file_version
                df = name_and_data_list[1]
                # save as csv file
                if file_version == ".csv":
                    self.save_database_csv(file=file, database=df)

                # save as excel file
                elif file_version == ".xlsx":
                    self.save_database_xlsx(file=file, database=df)

            except PermissionError:
                # failed to save, make a random addition to the name to save anyway
                random_genetator = random.Random()
                random_name = "random_"
                strings = ['a', "tgadg", "daf", "da", "gt", "ada", "fs", "dt", "d", "as"]
                name_lenght = random_genetator.randint(1, 14)

                # build the name
                for j in range(0, name_lenght):
                    random_genetator.shuffle(strings)
                    value = random_genetator.randint(0, 60000)
                    random_name += strings[j] + "_" + str(value) + "_"

                # save
                file = path + name_and_data_list[0] + random_name + file_version
                df = name_and_data_list[1]
                # save as csv file
                if file_version == ".csv":
                    self.save_database_csv(file=file, database=df)

                # save as excel file
                elif file_version == ".xlsx":
                    self.save_database_xlsx(file=file, database=df)

                # notify the user
                warnings.warn(f"Permission Error, saved with name {name_and_data_list[0] + random_name}", Warning)

        # add the experiment number for the next experiment
        self.count_experiment += 1

        print(f"Simulation data saved with name:    {exp_name}")
        if self.sim.print_info:
            print(f"\n\tINPUT THIS EXPERIMENT:      {self.sim.data_exp.order_input_counter}")
            print(f"\n\tOUTPUT THIS EXPERIMENT:     {self.sim.data_exp.order_output_counter}\n\n")

    def save_database_csv(self, file, database):
        database.to_csv(file, index=False)

    def save_database_xlsx(self, file, database):
        writer = pd.ExcelWriter(file, engine='xlsxwriter')
        database.to_excel(writer, sheet_name='name', index=False)
        writer.save()

    def get_directory(self):
        # define different path options
        machine_name = socket.gethostname()
        path = ""

        # find path for specific machine
        if machine_name == "LAPTOP-HN4N26LU":
            path = "C:/Users/Arno_ZenBook/Dropbox/Professioneel/Research/Results/test/"
        elif machine_name[0:7] == "pg-node":
            path = "/data/s3178471/"
        else:
            warnings.warn(f"{machine_name} is an unknown machine name ", Warning)
            path = os.path.abspath(os.getcwd())
            print(f"files are saved in {path}")
        return path
