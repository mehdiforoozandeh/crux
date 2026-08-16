# SortLab — t4 write a hello-world timi
import time

def main():
    t0 = time.perf_counter()
    print('t4 write a hello-world timi')
    print(round((time.perf_counter() - t0) * 1000, 3), 'ms')

if __name__ == '__main__':
    main()
