"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""
# range for each variable
alpha = [*range(0, 101, 1)]
alpha = [x / 100 for x in alpha]
# routing direction
routing_directions = ["GFS", "RJS", "PFS"]
# dispatching rule
dispatching_rule = ["FCFS", "ODD_land", "MODD", "SPT"]


# params
experimental_params_list = []

# IMM
for rd_i in routing_directions:
    for dr_i in dispatching_rule:
        params_list = []
        params_list.append(False)  # order release
        params_list.append(False)  # pp_02 off
        params_list.append(0)      # alpha
        params_list.append(rd_i)   # routing direction
        params_list.append(dr_i)   # dispatching_rule
        params_list.append("Immediate-release")
        experimental_params_list.append(params_list)

# PP_02
for alpha_i in alpha:
    for rd_i in routing_directions:
        params_list = []
        params_list.append(False)       # order release
        params_list.append(True)        # pp_02 on
        params_list.append(alpha_i)     # alpha
        params_list.append(rd_i)        # routing direction
        params_list.append("FCFS")        # dispatching_rule
        params_list.append("ThesisProject")
        experimental_params_list.append(params_list)

print(len(experimental_params_list))