# SortLab — t175 read the slope off each
import time

def main():
    t0 = time.perf_counter()
    print('t175 read the slope off each')
    print(round((time.perf_counter() - t0) * 1000, 3), 'ms')

if __name__ == '__main__':
    main()
