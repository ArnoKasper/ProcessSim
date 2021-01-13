import simulation_model as Simulation_Model

#### Order release method ----------------------------------------------------------------------------------------------
class Release_Control(object):

    def __init__(self, simulation):
        self.sim = simulation

    #### The order pool-------------------------------------------------------------------------------------------------
    def order_pool(self, sim, pool, order):
        # Set the priority for each job
        if self.sim.policy_pannel.sequencing_rule == "FCFS":
            Seq_Priority = order.id
        elif self.sim.policy_pannel.sequencing_rule == "SPT":
            Seq_Priority = list(order.process_time.values())[0]
        elif self.sim.policy_pannel.sequencing_rule == "PRD":
            Seq_Priority = order.PRD
        else:
            raise Exception('No sequencing rule in the pool selected')

        # Put each job in the pool
        job = [order, Seq_Priority]

        yield self.sim.model_pannel.ORDER_POOL.put(job)

        if self.sim.model_pannel.AGENT_CONTROL:
            if self.sim.agent.agent_online:
                # get first work centre
                WorkCentre = order.routing_sequence[0]

                # update state
                action = self.sim.agent.get_state(agent_online=True, get_action=True, WorkCentre=WorkCentre)

                # execute actions
                if action != 0:
                    self.sim.env.process(self.agent_release(amount=action, WorkCentre=WorkCentre))
                return

        # Feedback mechanism for continuous release
        if self.sim.policy_pannel.release_control_method == "LUMS_COR":
            if self.sim.model_pannel.queue_configuration == "SQ"\
                or self.sim.model_pannel.queue_configuration == "MS":
                if len(self.sim.model_pannel.MANUFACTURING_FLOOR[order.routing_sequence[0]].queue) + \
                        len(self.sim.model_pannel.MANUFACTURING_FLOOR[order.routing_sequence[0]].users) <= self.sim.policy_pannel.continuous_trigger:
                    WorkCenter = order.routing_sequence[0]
                    order.process = self.sim.env.process(self.sim.release_control.continuous_trigger(self.sim, self.sim.model_pannel.ORDER_POOL, WorkCenter))

            elif self.sim.model_pannel.queue_configuration == "MQ":
                queue = 0
                users = 0
                for i in range(0, self.sim.model_pannel.NUMBER_OF_MACHINES):
                    # get queue length and users of the machine
                    queue += len(self.sim.model_pannel.MANUFACTURING_FLOOR[order.routing_sequence[0]][i].queue)
                    users += len(self.sim.model_pannel.MANUFACTURING_FLOOR[order.routing_sequence[0]][i].users)

                # if the amount of orders in the station is below the threshold, activate release
                if queue + users <= self.sim.policy_pannel.continuous_trigger:
                    WorkCenter = order.routing_sequence[0]
                    order.process = self.sim.env.process(self.sim.release_control.continuous_trigger(self.sim, self.sim.model_pannel.ORDER_POOL, WorkCenter))

        elif self.sim.policy_pannel.release_control_method == "pure_continuous":
            order.process = self.sim.env.process(self.sim.release_control.continuous_release(self.sim, self.sim.model_pannel.ORDER_POOL))

        elif self.sim.policy_pannel.release_control_method == "CONWIP":
            order.process = self.sim.env.process(self.sim.release_control.CONWIP(self.sim, self.sim.model_pannel.ORDER_POOL))

        elif self.sim.policy_pannel.release_control_method == "CONLOAD":
            order.process = self.sim.env.process(self.sim.release_control.CONLOAD(self.sim, self.sim.model_pannel.ORDER_POOL))
        return

    # Method to remove the released orders from the order pool ---------------------------------------------------------
    def remove_from_pool(self, release_now, pool):
        # create a variable that is equal to a item that is removed from the pool
        identifier = release_now[0].id
        release_now.pop(0)

        # Remove the orders from the pool by filtering the item that needs to go out the pool
        released_used = yield pool.get(lambda released_used: released_used[0].id == identifier)

    # WLC: periodic release  -------------------------------------------------------------------------------------------
    def periodic_release(self, sim, pool):
        while True:
            if self.sim.model_pannel.AGENT_CONTROL and self.sim.env.now >= self.sim.model_pannel.WARM_UP_PERIOD:
                break
            else:
                # yield a timeout when there is a new periodic release period
                yield sim.env.timeout(sim.policy_pannel.check_period)
            # Reset the list of released orders
            release_now = []

            # Sequence the orders currently in the pool
            if not sim.policy_pannel.sequencing_rule == "FCFS":
                pool.items.sort(key=lambda jobs: jobs[1])

            # Contribute the load from each item in the pool
            for job in range(0, len(pool.items)):
                order = pool.items[job][0]

                #### release workload element --------------------------------------------------------------------------
                # Contribute the load from for each workstation
                for WC in order.routing_sequence:
                    sim.model_pannel.RELEASED[WC] += order.process_time[WC] / (order.routing_sequence.index(WC) + 1)

                order.release = True

                # The new load is compared to the norm
                for WC in order.routing_sequence:
                    if sim.model_pannel.RELEASED[WC] - sim.model_pannel.PROCESSED[WC] > sim.policy_pannel.release_norm:
                        order.release = False

                # If a norm has been violated the job is not released and the contributed load set back
                if order.release == False:
                    for WC in order.routing_sequence:
                        sim.model_pannel.RELEASED[WC] -= order.process_time[WC] / (order.routing_sequence.index(WC) + 1)

                # The released orders are collected into a list for release
                if order.release:
                    # Orders for released are collected into a list
                    release_now.append(order)

                    # The orders are send to the manufacturing process
                    order.process = sim.env.process(self.sim.manufacturing_process.manufacturing_process(order=order))

            # The released orders are removed from the pool using the remove from pool method
            for jobs in range(0, len(release_now)):
                sim.env.process(sim.release_control.remove_from_pool(release_now, pool))

    # WLC: continuous release  -----------------------------------------------------------------------------------------
    def continuous_release(self, sim, pool):
        # Reset the list of released orders

        release_now = []

        # Sequence the orders currently in the pool
        if not sim.policy_pannel.sequencing_rule == "FCFS":
            pool.items.sort(key=lambda jobs: jobs[1])

        # Contribute the load from each item in the pool
        for job in range(0, len(pool.items)):
            order = pool.items[job][0]

            #### release workload element --------------------------------------------------------------------------
            # Contribute the load from for each workstation
            for WC in order.routing_sequence:
                sim.model_pannel.RELEASED[WC] += order.process_time[WC] / (order.routing_sequence.index(WC) + 1)

            order.release = True

            # The new load is compared to the norm
            for WC in order.routing_sequence:
                if sim.model_pannel.RELEASED[WC] - sim.model_pannel.PROCESSED[WC] > sim.policy_pannel.release_norm:
                    order.release = False

            # If a norm has been violated the job is not released and the contributed load set back
            if order.release == False:
                for WC in order.routing_sequence:
                    sim.model_pannel.RELEASED[WC] -= order.process_time[WC] / (order.routing_sequence.index(WC) + 1)

            # The released orders are collected into a list for release
            if order.release:
                # Orders for released are collected into a list
                release_now.append(order)

                # The orders are send to the manufacturing process
                order.process = sim.env.process(self.sim.manufacturing_process.manufacturing_process(order=order))

        # The released orders are removed from the pool using the remove from pool method
        for jobs in range(0, len(release_now)):
            sim.env.process(sim.release_control.remove_from_pool(release_now, pool))
        #return raise Exception("This function is not yet finalized")

    # continuous_trigger (part of LUMS COR) ----------------------------------------------------------------------------
    def continuous_trigger(self, sim, pool, WorkCenter):
        while True:
            # Empty the release list
            release_now = []
            trigger = 1
            # Sort orders in the pool
            if not sim.policy_pannel.sequencing_rule == "FCFS":
                pool.items.sort(key=lambda jobs: jobs[1])

            # Control if there is any order available for the starving work centre from all items in the pool
            for job in range(0, len(pool.items)):
                order = pool.items[job][0]

                # If there is an order available, than it can be released
                if order.routing_sequence[0] == WorkCenter and trigger == 1:
                    trigger += 1
                    sim.data_run.ContLUMSCORCounter += 1
                    # Contribute the load to the workload measures
                    for WC in order.routing_sequence:
                        sim.model_pannel.RELEASED[WC] += order.process_time[WC] / (order.routing_sequence.index(WC) + 1)
                        order.release = True
                        # If an order turned out to be released, it is send to be removed from the pool
                    if order.release:
                        order.continous_trigger = True

                        # Add the order to the released list
                        release_now.append(order)

                        # Remove the order from the pool
                        sim.env.process(sim.release_control.remove_from_pool(release_now, pool))

                        # Send the order to the starting work centre
                        order.process = sim.env.process(self.sim.manufacturing_process.manufacturing_process(order=order))
            return
            yield

    def continuous_trigger_activation(self, sim, order, WorkCenter):
        # Feedback mechanism for continuous release
        if sim.model_pannel.queue_configuration == "SQ"\
                or sim.model_pannel.queue_configuration == "MS":
            # Control the if the the amount of orders in or before the work centre is equal or less than one
            if len(order.WorkCenterRQ.queue) + len(order.WorkCenterRQ.users) <= sim.policy_pannel.continuous_trigger:
                pool = sim.model_pannel.ORDER_POOL
                sim.env.process(sim.release_control.continuous_trigger(sim, pool, WorkCenter))

        elif sim.model_pannel.queue_configuration == "MQ":
            queue = 0
            users = 0
            for i in range(0, sim.model_pannel.NUMBER_OF_MACHINES):
                # get queue length and users of the machine
                queue += len(sim.model_pannel.MANUFACTURING_FLOOR[WorkCenter][i].queue)
                users += len(sim.model_pannel.MANUFACTURING_FLOOR[WorkCenter][i].users)

            # Control the if the the amount of orders in or before the work centre is equal or less than one
            if queue + users <= sim.policy_pannel.continuous_trigger:
                pool = sim.model_pannel.ORDER_POOL
                sim.env.process(sim.release_control.continuous_trigger(sim, pool, WorkCenter))

    # CONWIP MECHANISM -------------------------------------------------------------------------------------------------
    def CONWIP(self, sim, pool):
        while True:
            # Reset the list of released order
            release_now = []

            # Sequence the orders currently in the pool
            if not sim.policy_pannel.sequencing_rule == "FCFS":
                pool.items.sort(key=lambda jobs: jobs[1])

            # Contribute the load from each item in the pool
            for job in range(0, len(pool.items)):
                order = pool.items[job][0]

                # Contribute the load from for each workstation
                sim.model_pannel.RELEASED["WC1"] += 1
                order.Release = True

                # The new load is compared to the norm
                if sim.model_pannel.RELEASED["WC1"] - sim.model_pannel.PROCESSED["WC1"] > sim.policy_pannel.release_norm:
                    order.Release = False

                # If a norm has been violated the job is not released and the contributed load set back
                if order.Release == False:
                    sim.model_pannel.RELEASED["WC1"] -= 1

                # The released orders are collected into a list for release
                elif order.Release == True:
                    # Orders for released are collected into a list
                    release_now.append(order)

                    # The orders are send to the manufacturing process
                    sim.env.process(self.sim.manufacturing_process.manufacturing_process(order=order))

            # The released orders are removed from the pool using the remove from pool method
            for jobs in range(0, len(release_now)):
                sim.env.process(sim.release_control.remove_from_pool(release_now, pool))
            return
            yield

    # CONLOAD MECHANISM ------------------------------------------------------------------------------------------------
    def CONLOAD(self, sim, pool):
        while True:
            # Reset the list of released orders
            release_now = []

            # Sequence the orders currently in the pool
            if not sim.policy_pannel.sequencing_rule == "FCFS":
                pool.items.sort(key=lambda jobs: jobs[1])

            # Contribute the load from each item in the pool
            for job in range(0, len(pool.items)):
                order = pool.items[job][0]

                # Contribute the load from for each workstation ["WC1"] --> only use the first value of the library
                sim.model_pannel.RELEASED["WC1"] += order.process_time_cumulative
                order.Release = True

                # The new load is compared to the norm
                if sim.model_pannel.RELEASED["WC1"] - sim.model_pannel.PROCESSED["WC1"] > sim.policy_pannel.release_norm:
                    order.Release = False

                # If a norm has been violated the job is not released and the contributed load set back
                if order.Release == False:
                    GVar.RELEASED["WC1"] -= order.process_time_cumulative

                # The released orders are collected into a list for release
                elif order.Release == True:
                    # Orders for released are collected into a list
                    release_now.append(order)

                    # The orders are send to the manufacturing process
                    sim.env.process(self.sim.manufacturing_process.manufacturing_process(order=order))

            # The released orders are removed from the pool using the remove from pool method
            for jobs in range(0, len(release_now)):
                sim.env.process(ReleaseControl.remove_from_pool(release_now, pool))
            return
            yield

    # agent release ----------------------------------------------------------------------------------------------------
    def agent_release(self, WorkCentre, amount):
        while True:
            # Empty the release list
            release_now = []
            released_load = 0
            # Sort orders in the pool
            if not self.sim.policy_pannel.sequencing_rule == "FCFS":
                self.sim.model_pannel.ORDER_POOL.items.sort(key=lambda jobs: jobs[1])

            # Control if there is any order available for the starving work centre from all items in the pool
            for i, order in enumerate(self.sim.model_pannel.ORDER_POOL.items):
                order = order[0]

                # If there is an order available, than it can be released
                if order.routing_sequence[0] == WorkCentre and released_load < amount:
                    # Contribute the load from for each workstation
                    for WC in order.routing_sequence:
                        #self.sim.model_pannel.RELEASED[WC] += order.process_time[WC] / (order.routing_sequence.index(WC) + 1)
                        self.sim.model_pannel.RELEASED[WC] += order.process_time[WC]

                    order.release = True

                    # The new load is compared to the norm
                    released_load += order.process_time[WorkCentre]
                    if released_load > amount:
                        order.release = False

                    # If a norm has been violated the job is not released and the contributed load set back
                    if order.release == False:
                        released_load -= order.process_time[WorkCentre]
                        for WC in order.routing_sequence:
                            #self.sim.model_pannel.RELEASED[WC] -= order.process_time[WC] / (order.routing_sequence.index(WC) + 1)
                            self.sim.model_pannel.RELEASED[WC] -= order.process_time[WC]

                if order.release:
                    # contribute load to already released load
                    released_load += order.process_time[WorkCentre]
                    # Add the order to the released list
                    release_now.append(order)

                    # Remove the order from the pool
                    self.sim.env.process(self.sim.release_control.remove_from_pool(release_now, self.sim.model_pannel.ORDER_POOL))

                    # Send the order to the starting work centre
                    order.process = self.sim.env.process(self.sim.manufacturing_process.manufacturing_process(order=order))
            return
            yield
