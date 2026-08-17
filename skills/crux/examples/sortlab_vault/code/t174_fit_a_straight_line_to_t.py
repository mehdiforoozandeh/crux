# SortLab — t174 fit a straight line to t
import time

def main():
    t0 = time.perf_counter()
    print('t174 fit a straight line to t')
    print(round((time.perf_counter() - t0) * 1000, 3), 'ms')

if __name__ == '__main__':
    main()
