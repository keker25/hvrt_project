import sys
print("Python path:", sys.path)

try:
    import matplotlib
    print("Matplotlib version:", matplotlib.__version__)
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    print("Matplotlib imported successfully!")
    
    plt.figure()
    plt.plot([1,2,3])
    plt.savefig('logs/test_plot.png', dpi=100)
    print("Test plot saved!")
    
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()
