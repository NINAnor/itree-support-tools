from nodes import crown_condition, crown_structure, crown_to_stem


def tree(filegdb_path, v_crown):
    crown_structure(filegdb_path)
    crown_condition(filegdb_path, v_crown)
    crown_to_stem(filegdb_path)
    return


if __name__ == "__main__":
    pass
