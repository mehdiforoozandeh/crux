# SortLab — t61 add an early exit to bub
import time

def main():
    t0 = time.perf_counter()
    print('t61 add an early exit to bub')
    print(round((time.perf_counter() - t0) * 1000, 3), 'ms')

if __name__ == '__main__':
    main()
