def get_BL654_error_from_response(response):
    if '\t' in response:
        error = response.split('\t')[1].strip()
    try:
        error_code = int(error, 16)
        return get_BL654_error(error_code)
#    except ValueError as err: 
    except ValueError:
        pass
    return ""

    


def get_BL654_error(error):
    with open('bluetooth/codes.csv', 'r') as f:
        # the fist line doesn't have an error code
        f.readline()
        for line in f:
            code = line.split('=')
            try:
                err_code_int = int(code[0])
                if err_code_int == error:
                    return code[1]
#            except ValueError as err:
            except ValueError:
                pass
        return ""


if __name__ == "__main__":
    res = get_BL654_error(0xe007)
    print(res)
