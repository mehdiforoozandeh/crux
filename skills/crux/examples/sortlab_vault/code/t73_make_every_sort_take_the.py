# SortLab — t73 make every sort take the
import time

def main():
    t0 = time.perf_counter()
    print('t73 make every sort take the')
    print(round((time.perf_counter() - t0) * 1000, 3), 'ms')

if __name__ == '__main__':
    main()
