"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""
from operator import itemgetter

class ReleaseControl(object):
    def __init__(self, simulation):
        self.sim = simulation
        self.pool = self.sim.model_panel.ORDER_POOL

    def order_pool(self, order):
        """
        the the pool with flow items before the process
        :param order: order object found in order.py
        """
        # Set the priority for each job
        if self.sim.policy_panel.sequencing_rule == "FCFS":
            seq_priority = order.id
        elif self.sim.policy_panel.sequencing_rule == "SPT":
            seq_priority = list(order.process_time.values())[0]
        elif self.sim.policy_panel.sequencing_rule == "PRD":
            seq_priority = order.PRD
        elif self.sim.policy_panel.sequencing_rule == "Customized":
            seq_priority = self.sim.customized_settings.pool_seq_rule()
        else:
            raise Exception('No sequencing rule in the pool selected')

        # Put each job in the pool
        job = [order, seq_priority, 1]
        self.pool.put(job)

        # release mechanisms
        if self.sim.policy_panel.release_control_method == "LUMS_COR":
            # feedback mechanism for continuous release
            work_center = order.routing_sequence[0]
            if self.control_queue_empty(work_center=work_center):
                order.process = self.sim.env.process(
                    self.sim.release_control.continuous_trigger(work_center=work_center))
        elif self.sim.policy_panel.release_control_method == "pure_continuous":
            order.process = self.sim.env.process(self.sim.release_control.continuous_release())
        elif self.sim.policy_panel.release_control_method == "CONWIP":
            order.process = self.sim.env.process(self.sim.release_control.CONWIP())
        elif self.sim.policy_panel.release_control_method == "CONLOAD":
            order.process = self.sim.env.process(self.sim.release_control.CONLOAD())
        return

    def control_queue_empty(self, work_center):
        """
        controls if the queue is empty
        :param: work_center:
        :return: bool
        """
        in_system = len(self.sim.model_panel.ORDER_QUEUES[work_center].items) + \
                    len(self.sim.model_panel.MANUFACTURING_FLOOR[work_center].users)
        return in_system <= self.sim.policy_panel.continuous_trigger

    def remove_from_pool(self, release_now):
        """
        remove flow item from the pool
        :param release_now: list with parameters of the flow item
        """
        # create a variable that is equal to a item that is removed from the pool
        release_now[2] = 0
        # sort the queue
        self.pool.items.sort(key=itemgetter(2))
        # remove flow item from pool
        self.pool.get()

    def periodic_release(self):
        """
        Workload Control Periodic release using aggregate load. See workings in Land 2004.
        """
        periodic_interval = self.sim.policy_panel.check_period
        while True:
            yield self.sim.env.timeout(periodic_interval)
            # Reset the list of released orders
            release_now = []

            # Sequence the orders currently in the pool
            if not self.sim.policy_panel.sequencing_rule == "FCFS":
                self.pool.items.sort(key=itemgetter(1))

            # Contribute the load from each item in the pool
            for i, order_list in enumerate(self.pool.items):
                order = order_list[0]

                # release workload element --------------------------------------------------------------------------
                # Contribute the load from for each workstation
                for WC in order.routing_sequence:
                    self.sim.model_panel.RELEASED[WC] += order.process_time[WC] / (order.routing_sequence.index(WC) + 1)

                order.release = True

                # The new load is compared to the norm
                for WC in order.routing_sequence:
                    if self.sim.model_panel.RELEASED[WC] - self.sim.model_panel.PROCESSED[WC] \
                            > self.sim.policy_panel.release_norm:
                        order.release = False

                # If a norm has been violated the job is not released and the contributed load set back
                if not order.release:
                    for WC in order.routing_sequence:
                        self.sim.model_panel.RELEASED[WC] -= order.process_time[WC] / (
                                order.routing_sequence.index(WC) + 1)

                # The released orders are collected into a list for release
                if order.release:
                    # Orders for released are collected into a list
                    release_now.append(order_list)

                    # The orders are send to the process
                    self.sim.process.put_in_queue(order=order)

            # The released orders are removed from the pool using the remove from pool method
            for _, jobs in enumerate(release_now):
                self.sim.release_control.remove_from_pool(release_now=jobs)

    def continuous_release(self):
        """
        Workload Control: continuous release using aggregate load. See workings in Thürer et al, 2012
        """
        # Reset the list of released orders
        release_now = []

        # Sequence the orders currently in the pool
        if not self.sim.policy_panel.sequencing_rule == "FCFS":
            self.pool.items.sort(key=itemgetter(1))

        # Contribute the load from each item in the pool
        for i, order_list in enumerate(self.pool.items):
            order = order_list[0]

            # release workload element
            # Contribute the load from for each workstation
            for WC in order.routing_sequence:
                self.sim.model_panel.RELEASED[WC] += order.process_time[WC] / (order.routing_sequence.index(WC) + 1)

            order.release = True

            # The new load is compared to the norm
            for WC in order.routing_sequence:
                if self.sim.model_panel.RELEASED[WC] - self.sim.model_panel.PROCESSED[WC] > \
                        self.sim.policy_panel.release_norm:
                    order.release = False

            # If a norm has been violated the job is not released and the contributed load set back
            if not order.release:
                for WC in order.routing_sequence:
                    self.sim.model_panel.RELEASED[WC] -= order.process_time[WC] / (order.routing_sequence.index(WC) + 1)

            # The released orders are collected into a list for release
            if order.release:
                # Orders for released are collected into a list
                release_now.append(order_list)

                # The orders are send to the process
                self.sim.process.put_in_queue(order=order)

        # The released orders are removed from the pool using the remove from pool method
        for _, jobs in enumerate(release_now):
            self.sim.release_control.remove_from_pool(release_now=jobs)

    def continuous_trigger(self, work_center):
        """
        Workload Control: continuous release using aggregate load. See workings in Thürer et al, 2014.
        Part of LUMS COR
        """
        while True:
            # empty the release list
            trigger = 1
            # sort orders in the pool
            if not self.sim.policy_panel.sequencing_rule == "FCFS":
                self.pool.items.sort(key=itemgetter(1))

            # control if there is any order available for the starving work centre from all items in the pool
            for i, order_list in enumerate(self.pool.items):
                order = order_list[0]

                # if there is an order available, than it can be released
                if order.routing_sequence[0] == work_center and trigger == 1:
                    trigger += 1
                    self.sim.data_run.ContLUMSCORCounter += 1
                    # contribute the load to the workload measures
                    for WC in order.routing_sequence:
                        self.sim.model_panel.RELEASED[WC] += order.process_time[WC] / (
                                order.routing_sequence.index(WC) + 1)
                        order.release = True
                        # if an order turned out to be released, it is send to be removed from the pool
                    if order.release:
                        order.continuous_trigger = True
                        # Send the order to the starting work centre
                        self.sim.process.put_in_queue(order=order)
                        # release order from the pool
                        self.sim.release_control.remove_from_pool(release_now=order_list)
            return
            yield

    def continuous_trigger_activation(self, order, work_center):
        """
        feedback mechanism for continuous release
        :param work_center:
        """
        # control the if the the amount of orders in or before the work centre is equal or less than one
        if self.control_queue_empty(work_center=work_center):
            self.sim.env.process(self.sim.release_control.continuous_trigger(work_center=work_center))

    def CONWIP(self):
        """
        Constant Work In Process. Fixed amount of flow units in the system, see Spearman et al. (1998)
        """
        while True:
            # Reset the list of released order
            release_now = []

            # Sequence the orders currently in the pool
            if not self.sim.policy_panel.sequencing_rule == "FCFS":
                self.pool.items.sort(key=itemgetter(1))

            # Contribute the load from each item in the pool
            for i, order_list in enumerate(self.pool.items):
                order = order_list[0]

                # Contribute the load from for each workstation
                self.sim.model_panel.RELEASED["WC1"] += 1
                order.Release = True

                # The new load is compared to the norm
                if self.sim.model_panel.RELEASED["WC1"] - self.sim.model_panel.PROCESSED["WC1"] > \
                        self.sim.policy_panel.release_norm:
                    order.Release = False

                # If a norm has been violated the job is not released and the contributed load set back
                if not order.Release:
                    self.sim.model_panel.RELEASED["WC1"] -= 1

                # The released orders are collected into a list for release
                elif order.Release:
                    # Orders for released are collected into a list
                    release_now.append(order_list)

                    # The orders are send to the manufacturing
                    self.sim.process.put_in_queue(order=order)

            # The released orders are removed from the pool using the remove from pool method
            for _, jobs in enumerate(release_now):
                self.sim.release_control.remove_from_pool(release_now=jobs)
            return
            yield

    def CONLOAD(self, sim, pool):
        """
        Constant Work In Workload. Fixed amount of process time in the system, see Spearman et al. (1998)
        """
        while True:
            # Reset the list of released orders
            release_now = []

            # Sequence the orders currently in the pool
            if not sim.policy_panel.sequencing_rule == "FCFS":
                self.pool.items.sort(key=itemgetter(1))

            # Contribute the load from each item in the pool
            for i, order_list in enumerate(self.pool.items):
                order = order_list[0]

                # Contribute the load from for each workstation ["WC1"] --> only use the first value of the library
                self.sim.model_panel.RELEASED["WC1"] += order.process_time_cumulative
                order.Release = True

                # The new load is compared to the norm
                if self.sim.model_panel.RELEASED["WC1"] - self.sim.model_panel.PROCESSED["WC1"] > \
                        self.sim.policy_panel.release_norm:
                    order.Release = False

                # If a norm has been violated the job is not released and the contributed load set back
                if not order.Release:
                    GVar.RELEASED["WC1"] -= order.process_time_cumulative

                # The released orders are collected into a list for release
                elif order.Release:
                    # Orders for released are collected into a list
                    release_now.append(order_list)

                    # The orders are send to the process
                    self.sim.process.put_in_queue(order=order)

            # The released orders are removed from the pool using the remove from pool method
            for _, jobs in enumerate(release_now):
                self.sim.release_control.remove_from_pool(release_now=jobs)
            return
            yield

    def finished_load(self, order, work_center):
        """
        add the processed load and trigger continuous release if required.
        :param order:
        :param work_center:
        :return:
        """
        # remove load
        if self.sim.policy_panel.release_control_method == "CONWIP" and len(order.routing_sequence == 0):
            self.sim.model_panel.PROCESSED["WC1"] += 1
        elif self.sim.policy_panel.release_control_method == "CONLOAD" and len(order.routing_sequence == 0):
            self.sim.model_panel.PROCESSED["WC1"] += order.process_time_cumulative
        else:
            self.sim.model_panel.PROCESSED[work_center] += order.process_time[work_center] / (
                    order.routing_sequence_data.index(work_center) + 1)
        # continuous trigger LUMS COR
        if self.sim.policy_panel.release_control_method == "LUMS_COR":
            self.sim.release_control.continuous_trigger_activation(order=order, work_center=work_center)
        return
