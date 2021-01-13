"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""

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
            Seq_Priority = order.id
        elif self.sim.policy_panel.sequencing_rule == "SPT":
            Seq_Priority = list(order.process_time.values())[0]
        elif self.sim.policy_panel.sequencing_rule == "PRD":
            Seq_Priority = order.PRD
        elif self.sim.policy_panel.sequencing_rule == "Customized":
            Seq_Priority = order.PRD
        else:
            raise Exception('No sequencing rule in the pool selected')

        # Put each job in the pool
        job = [order, Seq_Priority]
        yield self.pool.put(job)

        # release mechanisms
        if self.sim.policy_panel.release_control_method == "LUMS_COR":
            # feedback mechanism for continuous release
            if len(self.sim.model_panel.MANUFACTURING_FLOOR[order.routing_sequence[0]].queue) + \
                    len(self.sim.model_panel.MANUFACTURING_FLOOR[order.routing_sequence[0]].users) \
                    <= self.sim.policy_panel.continuous_trigger:
                work_center = order.routing_sequence[0]
                order.process = self.sim.env.process(self.sim.release_control.continuous_trigger(work_center=work_center))
        elif self.sim.policy_panel.release_control_method == "pure_continuous":
            order.process = self.sim.env.process(self.sim.release_control.continuous_release())
        elif self.sim.policy_panel.release_control_method == "CONWIP":
            order.process = self.sim.env.process(self.sim.release_control.CONWIP())
        elif self.sim.policy_panel.release_control_method == "CONLOAD":
            order.process = self.sim.env.process(self.sim.release_control.CONLOAD())
        return

    def remove_from_pool(self, release_now):
        """
        remove flow item from the pool
        :param release_now: list with parameters of the flow item
        """
        # create a variable that is equal to a item that is removed from the pool
        identifier = release_now[0].identifier
        release_now.pop(0)

        # Remove the orders from the pool by filtering the item that needs to go out the pool
        released_used = yield self.pool.get(lambda released_used: released_used[0].identifier == identifier)

    # WLC: periodic release  -------------------------------------------------------------------------------------------
    def periodic_release(self):
        """
        Workload Control Periodic release using aggregate load. See workings in Land 2004.
        """
        periodic_interval = self.sim.policy_panel.check_period
        while True:
            if self.sim.env.now >= self.sim.model_panel.WARM_UP_PERIOD:
                break
            else:
                # yield a timeout when there is a new periodic release period
                yield self.sim.env.timeout(periodic_interval)
            # Reset the list of released orders
            release_now = []

            # Sequence the orders currently in the pool
            if not self.sim.policy_panel.sequencing_rule == "FCFS":
                self.pool.items.sort(key=lambda jobs: jobs[1])

            # Contribute the load from each item in the pool
            for job in range(0, len(self.pool.items)):
                order = self.pool.items[job][0]

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
                        self.sim.model_panel.RELEASED[WC] -= order.process_time[WC] / (order.routing_sequence.index(WC) + 1)

                # The released orders are collected into a list for release
                if order.release:
                    # Orders for released are collected into a list
                    release_now.append(order)

                    # The orders are send to the manufacturing process
                    order.process = self.sim.env.process(
                        self.sim.process.put_in_queue(order=order)
                    )

            # The released orders are removed from the pool using the remove from pool method
            for jobs in range(0, len(release_now)):
                self.sim.env.process(self.sim.release_control.remove_from_pool(release_now))

    # WLC: continuous release  -----------------------------------------------------------------------------------------
    def continuous_release(self):
        """
        Workload Control: continuous release using aggregate load. See workings in Thürer et al, 2012
        """
        # Reset the list of released orders
        release_now = []

        # Sequence the orders currently in the pool
        if not self.sim.policy_panel.sequencing_rule == "FCFS":
            self.pool.items.sort(key=lambda jobs: jobs[1])

        # Contribute the load from each item in the pool
        for job in range(0, len(self.pool.items)):
            order = self.pool.items[job][0]

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
                release_now.append(order)

                # The orders are send to the manufacturing process
                order.process = self.sim.env.process(
                    self.sim.process.put_in_queue(order=order)
                )

        # The released orders are removed from the pool using the remove from pool method
        for jobs in range(0, len(release_now)):
            self.sim.env.process(self.sim.release_control.remove_from_pool(release_now))

    # continuous_trigger (part of LUMS COR) ----------------------------------------------------------------------------
    def continuous_trigger(self, work_center):
        """
        Workload Control: continuous release using aggregate load. See workings in Thürer et al, 2014.
        Part of LUMS COR
        """
        while True:
            # Empty the release list
            release_now = []
            trigger = 1
            # Sort orders in the pool
            if not self.sim.policy_panel.sequencing_rule == "FCFS":
                self.pool.items.sort(key=lambda jobs: jobs[1])

            # Control if there is any order available for the starving work centre from all items in the pool
            for job in range(0, len(self.pool.items)):
                order = self.pool.items[job][0]

                # If there is an order available, than it can be released
                if order.routing_sequence[0] == work_center and trigger == 1:
                    trigger += 1
                    self.sim.data_run.ContLUMSCORCounter += 1
                    # Contribute the load to the workload measures
                    for WC in order.routing_sequence:
                        self.sim.model_panel.RELEASED[WC] += order.process_time[WC] / (order.routing_sequence.index(WC) + 1)
                        order.release = True
                        # If an order turned out to be released, it is send to be removed from the pool
                    if order.release:
                        order.continuous_trigger = True

                        # Add the order to the released list
                        release_now.append(order)

                        # Remove the order from the pool
                        self.sim.env.process(self.sim.release_control.remove_from_pool(release_now))

                        # Send the order to the starting work centre
                        order.process = self.sim.env.process(
                            self.sim.process.put_in_queue(order=order)
                        )
            return
            yield

    def continuous_trigger_activation(self, order, work_center):
        """
        feedback mechanism for continuous release
        :param work_center:
        """
        # control the if the the amount of orders in or before the work centre is equal or less than one
        if len(order.WorkCenterRQ.queue) + len(order.WorkCenterRQ.users) <= self.sim.policy_panel.continuous_trigger:
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
                self.pool.items.sort(key=lambda jobs: jobs[1])

            # Contribute the load from each item in the pool
            for job in range(0, len(self.pool.items)):
                order = self.pool.items[job][0]

                # Contribute the load from for each workstation
                self.sim.model_panel.RELEASED["WC1"] += 1
                order.Release = True

                # The new load is compared to the norm
                if self.sim.model_panel.RELEASED["WC1"] - self.sim.model_panel.PROCESSED["WC1"] > \
                        self.sim.policy_panel.release_norm:
                    order.Release = False

                # If a norm has been violated the job is not released and the contributed load set back
                if order.Release == False:
                    self.sim.model_panel.RELEASED["WC1"] -= 1

                # The released orders are collected into a list for release
                elif order.Release == True:
                    # Orders for released are collected into a list
                    release_now.append(order)

                    # The orders are send to the manufacturing process
                    self.sim.env.process(
                        self.sim.process.put_in_queue(order=order)
                    )

            # The released orders are removed from the pool using the remove from pool method
            for jobs in range(0, len(release_now)):
                self.sim.env.process(self.sim.release_control.remove_from_pool(release_now))
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
                self.pool.items.sort(key=lambda jobs: jobs[1])

            # Contribute the load from each item in the pool
            for job in range(0, len(self.pool.items)):
                order = self.pool.items[job][0]

                # Contribute the load from for each workstation ["WC1"] --> only use the first value of the library
                self.sim.model_panel.RELEASED["WC1"] += order.process_time_cumulative
                order.Release = True

                # The new load is compared to the norm
                if self.sim.model_panel.RELEASED["WC1"] - self.sim.model_panel.PROCESSED["WC1"] > \
                        self.sim.policy_panel.release_norm:
                    order.Release = False

                # If a norm has been violated the job is not released and the contributed load set back
                if order.Release == False:
                    GVar.RELEASED["WC1"] -= order.process_time_cumulative

                # The released orders are collected into a list for release
                elif order.Release == True:
                    # Orders for released are collected into a list
                    release_now.append(order)

                    # The orders are send to the manufacturing process
                    self.sim.env.process(self.sim.process.put_in_queue(order=order))

            # The released orders are removed from the pool using the remove from pool method
            for jobs in range(0, len(release_now)):
                self.sim.env.process(self.sim.release_control.remove_from_pool(release_now))
            return
            yield
