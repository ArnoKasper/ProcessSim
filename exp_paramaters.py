""""
Made by: Arno Kasper
Version 1.0
Date 07/03/2020

- Corrected and validated
"""

# range for each variable
Exp_var_1 = [*range(3, 21, 3)]
Exp_var_2 = [*(range(70, 85, 5))]
Exp_var_2 = [x / 10 for x in Exp_var_2]
experimental_params_list = []

# Experimental variable 1
for exp_var_1 in Exp_var_1:

    # Experimental variable 2
    for exp_var_2 in Exp_var_2:
        params_list = []
        params_list.append(False)
        params_list.append(exp_var_1)
        params_list.append(exp_var_2)
        params_list.append("Immediate-release")
        experimental_params_list.append(params_list)

# Experimental variable 1
for exp_var_1 in Exp_var_1:

    # Experimental variable 2
    for exp_var_2 in Exp_var_2:
        params_list = []
        params_list.append(True)
        params_list.append(exp_var_1)
        params_list.append(exp_var_2)
        params_list.append("control-novel-beta")
        experimental_params_list.append(params_list)

# Experimental variable 1
for exp_var_1 in Exp_var_1:

    # Experimental variable 2
    for exp_var_2 in Exp_var_2:
        params_list = []
        params_list.append(True)
        params_list.append(exp_var_1)
        params_list.append(exp_var_2)
        params_list.append("LUMS_COR")
        experimental_params_list.append(params_list)

print(len(experimental_params_list))