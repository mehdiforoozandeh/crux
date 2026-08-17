# SortLab — t63 count swaps inside each
import time

def main():
    t0 = time.perf_counter()
    print('t63 count swaps inside each')
    print(round((time.perf_counter() - t0) * 1000, 3), 'ms')

if __name__ == '__main__':
    main()
