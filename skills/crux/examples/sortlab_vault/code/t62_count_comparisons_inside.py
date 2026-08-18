# SortLab — t62 count comparisons inside
import time

def main():
    t0 = time.perf_counter()
    print('t62 count comparisons inside')
    print(round((time.perf_counter() - t0) * 1000, 3), 'ms')

if __name__ == '__main__':
    main()
