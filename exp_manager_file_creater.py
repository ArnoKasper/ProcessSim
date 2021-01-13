#import exp_paramaters_report_summer_school as exp_dat

# Get the number of experiments from the experimental settings file
NUMBER_EXP = 100 #len(exp_dat.experimental_params_list)
MAX_NUMBER_JOBS = 1000
EXP_PER_JOB = 1

PATH = path = "C:/Users/Arno_ZenBook/Dropbox/Professioneel/Research/Model/peregrine_files/exp_manager_array_files_mdas/"

# Set looping variables
Exp_list = []
lower_limit = 0
upper_limit = 0 + EXP_PER_JOB - 1

# Create file information
for i in range(0, NUMBER_EXP):
    Exp_spec_list = []
    Exp_spec_list.append(lower_limit)
    Exp_spec_list.append(upper_limit)
    lower_limit += 1 + EXP_PER_JOB - 1
    upper_limit += 1 + EXP_PER_JOB - 1
    Exp_list.append(Exp_spec_list)

# Open template of the experiment manager
counter = 1

# Create a copy of the template with unique information
for i in range(0, len(Exp_list)):
    exp_lower_limit = Exp_list[i][0]
    exp_upper_limit = Exp_list[i][1]


    exp_name = f"peregrine_exp_manager_{counter}.py"
    name_path = PATH + exp_name

    counter += 1

    with open(name_path, "w+") as file:
        string_exp_lower_limit = f"start_exp_index: int = {exp_lower_limit}"
        string_exp_upper_limit = f"end_exp_index: int = {exp_upper_limit}"

        file.write(string_exp_lower_limit)
        file.write("\n")
        file.write(string_exp_upper_limit)
        file.write("\n")
        with open("C:/Users/Arno_ZenBook/Dropbox/Professioneel/Research/Model/peregrine_files/empty_exp_activation_mdas.txt", "r") as template_file:
            for line in template_file:
                file.write(line)

            file.close()
            template_file.close()


print(f"SET ARRAY TO: --array=1-{counter-1}")
