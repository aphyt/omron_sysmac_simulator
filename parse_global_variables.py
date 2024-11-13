

if __name__ == '__main__':
    variable_dictionary = {}
    with open('global_variables.txt', 'r') as file:
        next(file)
        for line in file:
            tokens = line.rstrip().split()
            if len(tokens) > 1:
                variable_dictionary[tokens[0]] = tokens[1]

    print(variable_dictionary)