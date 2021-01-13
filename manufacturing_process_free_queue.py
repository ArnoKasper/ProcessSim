from operator import itemgetter

class Manufacturing_Process_free_queue(object):
    def __init__(self, simulation):
        """:key
        params
        """
        self.sim = simulation
        self.Dispatching_Rule = 'FCFS'

    def put_in_pool(self, order):
        if order.first_entry:
            # first time entering the floor
            order.release_time = self.sim.env.now
            order.pool_time = order.release_time - order.entry_time
            order.first_entry = False

        # get work centre
        WorkCenter = order.routing_sequence[0]
        # control if the order can be released
        if len(self.sim.model_pannel.MANUFACTURING_FLOOR[WorkCenter].users) == 0:
            if len(self.sim.model_pannel.ORDER_POOL[WorkCenter].items) == 0:
                order.process = self.sim.env.process(self.sim.manufacturing_process.manufacturing_process(order=order, WorkCenter=WorkCenter))
            else:
                # put back into the pool
                pool_item = self.pool_list(order=order)
                self.sim.model_pannel.ORDER_POOL[WorkCenter].put(pool_item)
                self.dispatch_order(WorkCenter=WorkCenter)
                return
        # put in the pool
        else:
            # put back into the pool
            pool_item = self.pool_list(order=order)
            yield self.sim.model_pannel.ORDER_POOL[WorkCenter].put(pool_item)
            return

    def release_from_pool(self, WorkCenter):
        # sort the pool
        self.sim.model_pannel.ORDER_POOL[WorkCenter].items.sort(key=itemgetter(4))
        released_used = self.sim.model_pannel.ORDER_POOL[WorkCenter].get()
        return

    def pool_list(self, order):
        # select dispatching rule
        if self.Dispatching_Rule == "FCFS":
            order.dispatching_priority = order.identifier
        elif self.Dispatching_Rule == "SPT":
            order.dispatching_priority = order.process_time[order.routing_sequence[0]]
        elif self.Dispatching_Rule == "ODD":
            order.dispatching_priority = order.ODDs[order.routing_sequence[0]]
        elif self.Dispatching_Rule == "Define":
            order.dispatching_priority = "spam"
        else:
            raise Exception("no valid dispatching rule defined")

        # define pool object
        pool_item = [order,  # order object
                     order.dispatching_priority,  # order priority
                     order.routing_sequence[0],  # next step
                     1  # release from pool integer
                     ]
        return pool_item

    def dispatch_order(self, WorkCenter):
        # get new order for release
        order_list, break_loop, free_load = self.get_most_urgent_order(WorkCenter=WorkCenter)
        # no orders in pool
        if break_loop:
            return

        order = order_list[0]

        self.release_from_pool(WorkCenter=order.routing_sequence[0])
        order.process = self.sim.env.process(self.sim.manufacturing_process.manufacturing_process(order=order, WorkCenter=order.routing_sequence[0]))
        return

    def get_most_urgent_order(self, WorkCenter):
        # setup params
        urgency_list_1 = list()

        # if there are no items in the pool, return
        if len(self.sim.model_pannel.ORDER_POOL[WorkCenter].items) == 0:
            return None, True, False

        # I.) find most urgent order in the pool------------------------------------------------------------------------
        for i, order in enumerate(self.sim.model_pannel.ORDER_POOL[WorkCenter].items):
            order_list = order
            if len(order_list[0].routing_sequence) <= 1:
                order_list[3] = "NA"
            else:
                order_list[3] = order_list[0].routing_sequence[1]
            urgency_list_1.append(order_list)

        count = 0
        urgency_list_2 = sorted(urgency_list_1, key=itemgetter(1))  # sort according to ODD
        order = urgency_list_1[0]
        # set to zero to pull out of pull
        order[4] = 0
        return order, False, True

    def manufacturing_process(self, order, WorkCenter):
        # set params
        order.WorkCenterRQ = self.sim.model_pannel.MANUFACTURING_FLOOR[WorkCenter]
        order.dispatching_priority = order.ODDs[WorkCenter]
        req = order.WorkCenterRQ.request(priority=order.dispatching_priority)
        req.self = order

        # Yield a request
        with req as req:
            yield req
            # Request is finished, order is put into the que or directly processed
            yield self.sim.env.timeout(order.process_time[WorkCenter])
            # order is finished and released from the machine

        # update the routing list to avoid re-entrance
        order.machine_route[WorkCenter] = "PASSED"
        order.routing_sequence.remove(WorkCenter)

        # collect data
        self.data_collection_intermediate(order=order, WorkCenter=WorkCenter)

        # next action for the order
        if len(order.routing_sequence) == 0:
            self.data_collection_final(order=order)
        else:
            # activate new release
            order.process = self.sim.env.process(self.put_in_pool(order=order))

        # next action for the work centre
        self.release_load(WorkCenter=WorkCenter)
        return

    def data_collection_intermediate(self, order, WorkCenter):
        orderstarttime = self.sim.env.now - order.process_time[WorkCenter]
        order.order_start_time[WorkCenter] = orderstarttime
        order.proc_finished_time[WorkCenter] = self.sim.env.now
        order.queue_time[WorkCenter] = order.order_start_time[WorkCenter] - order.queue_entry_time[WorkCenter]
        return

    def data_collection_final(self, order):
        # Time collection registration
        order.finishing_time = self.sim.env.now
        self.sim.data_run.order_output_counter += 1

        # General data collection
        self.sim.data_run.Number += 1
        self.sim.data_run.CalculateUtiliz += order.process_time_cumulative

        if self.sim.model_pannel.CollectBasicData:
            self.sim.data_run.GrossThroughputTime.append(order.finishing_time - order.entry_time)
            self.sim.data_run.pooltime.append(order.pool_time)
            self.sim.data_run.ThroughputTime.append(order.finishing_time - order.release_time)
            self.sim.data_run.Lateness.append(order.finishing_time - order.due_date)
            if order.finishing_time - order.due_date > 0:
                MeanTardiness = order.finishing_time - order.due_date
                self.sim.data_run.NumberTardy += 1
            else:
                MeanTardiness = 0
            self.sim.data_run.Tardiness.append(MeanTardiness)
            self.sim.data_run.CumTardiness += MeanTardiness
            # Collection station data
            if self.sim.model_pannel.CollectStationData:
                self.sim.data_collection.station_data_collection(order=order)

        # Collect order data
        if self.sim.model_pannel.CollectOrderData:
            self.sim.data_collection.order_data_collection(order=order)

        # Collect flow data
        if self.sim.model_pannel.CollectFlowData:
            self.sim.data_collection.Data_Collection.flow_data_collection(sim=self.sim)

        # collect tracking data
        if self.sim.model_pannel.CollectMachineData:
            self.sim.data_collection.machine_data_collection(sim=self.sim)

        # collect discrete data
        if self.sim.model_pannel.CollectDiscreteData and self.sim.warm_up == False:
            value = order.finishing_time - order.due_date
            self.sim.data_collection.discrete_data_collection(sim=self.sim, value=value)

        self.sim.data_exp.order_output_counter += 1
        return