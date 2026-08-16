# SortLab — t56 test each sort on a list
import time

def main():
    t0 = time.perf_counter()
    print('t56 test each sort on a list')
    print(round((time.perf_counter() - t0) * 1000, 3), 'ms')

if __name__ == '__main__':
    main()
