# SortLab — t64 add a middle-item pivot
import time

def main():
    t0 = time.perf_counter()
    print('t64 add a middle-item pivot')
    print(round((time.perf_counter() - t0) * 1000, 3), 'ms')

if __name__ == '__main__':
    main()
