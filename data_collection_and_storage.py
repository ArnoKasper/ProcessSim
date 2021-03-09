"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""
from typing import cast, Dict, List, Optional, Tuple, Type, Generator
import pandas as pd

class DataStorageRun(object):
    def __init__(self, sim):
        self.sim = sim

        # General data
        self.run_number = list()
        self.accumulated_process_time = 0

        # old variables, still required?
        self.ContLUMSCORCounter = 0
        self.order_input_counter = 0
        self.order_output_counter = 0

        # order data
        self.order_list = list()

class DataStorageExp(object):
    def __init__(self, sim):
        self.sim = sim

        # general info
        self.order_input_counter = 0
        self.order_output_counter = 0

        # pandas dataframe
        self.database = None

class DataCollection(object):
    def __init__(self, simulation):
        self.sim = simulation

        # basic name list
        self.columns_names_run = [
                            "identifier",
                            "throughput_time",
                            "pool_time",
                            "process_throughput_time",
                            "lateness",
                            "tardiness",
                            "tardy",
                            ]

        # add work centre info if required
        if self.sim.model_panel.COLLECT_STATION_DATA:
            for i, _ in enumerate(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT):
                self.columns_names_run.append(f"queue_time_wc{i}")

    def append_run_list(self, result_list):
        self.sim.data_run.order_list.append(result_list)
        return

    def run_update(self, warmup):
        if not warmup:
            # update database
            self.store_run_data()

        # data processing finished. Update new run
        self.sim.data_run = DataStorageRun(sim=self.sim)
        return

    def store_run_data(self):
        # put all data into dataframe
        df_run = pd.DataFrame(self.sim.data_run.order_list)
        df_run.columns = self.columns_names_run

        # dataframe for each run
        df = pd.DataFrame(
            [(int(self.sim.env.now / (self.sim.model_panel.WARM_UP_PERIOD + self.sim.model_panel.RUN_TIME)))],
            columns=['run'])

        if self.sim.model_panel.COLLECT_BASIC_DATA and not self.sim.model_panel.COLLECT_ORDER_DATA:
            df["nr_flow_items"] = df_run.shape[0]
            number_of_machines_in_process = (
                        self.sim.model_panel.NUMBER_OF_MACHINES * len(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT))
            df["utilization"] = ((self.sim.data_run.accumulated_process_time * 100 / number_of_machines_in_process)
                                 / self.sim.model_panel.RUN_TIME)
            df["mean_throughput_time"] = df_run.loc[:, "throughput_time"].mean()
            df["var_throughput_time"] = df_run.loc[:, "throughput_time"].var()
            df["mean_pool_time"] = df_run.loc[:, "pool_time"].mean()
            df["var_pool_time"] = df_run.loc[:, "pool_time"].var()
            df["mean_process_throughput_time"] = df_run.loc[:, "process_throughput_time"].mean()
            df["var_process_throughput_time"] = df_run.loc[:, "process_throughput_time"].var()
            df["mean_lateness"] = df_run.loc[:, "lateness"].mean()
            df["var_lateness"] = df_run.loc[:, "lateness"].var()
            df["mean_tardiness"] = df_run.loc[:, "tardiness"].mean()
            df["var_tardiness"] = df_run.loc[:, "tardiness"].var()
            df["percentage_tardy"] = df_run.loc[:, "tardy"].sum() / df_run.shape[0]

            if self.sim.model_panel.COLLECT_STATION_DATA:
                for i, WC in enumerate(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT):
                    df[f"mean_queue_time_wc{i}"] = df_run.loc[:, f"queue_time_wc{i}"].mean()
                    df[f"var_queue_time_wc{i}"] = df_run.loc[:, f"queue_time_wc{i}"].var()

        if self.sim.model_panel.CUSTOM_CONTROL:
            df_extra = self.sim.customized_settings.add_additional_measures(df_run=df_run).reset_index(drop=True)
            df = pd.concat([df, df_extra], axis=1)

        # save data from the run
        if self.sim.data_exp.database is None:
            self.sim.data_exp.database = df
        else:
            self.sim.data_exp.database = pd.concat([self.sim.data_exp.database, df], ignore_index=True)

        # data processing finished. Update new run
        self.sim.data_run = DataStorageRun(sim=self.sim)
        return