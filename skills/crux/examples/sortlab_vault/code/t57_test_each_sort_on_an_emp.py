# SortLab — t57 test each sort on an emp
import time

def main():
    t0 = time.perf_counter()
    print('t57 test each sort on an emp')
    print(round((time.perf_counter() - t0) * 1000, 3), 'ms')

if __name__ == '__main__':
    main()
