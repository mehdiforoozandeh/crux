# SortLab — t59 fix the off-by-one bug i
import time

def main():
    t0 = time.perf_counter()
    print('t59 fix the off-by-one bug i')
    print(round((time.perf_counter() - t0) * 1000, 3), 'ms')

if __name__ == '__main__':
    main()
