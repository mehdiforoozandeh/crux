# SortLab — t52 write merge sort
import time

def main():
    t0 = time.perf_counter()
    print('t52 write merge sort')
    print(round((time.perf_counter() - t0) * 1000, 3), 'ms')

if __name__ == '__main__':
    main()
