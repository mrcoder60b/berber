import traceback
try:
    import app
    print('Import successful')
except Exception as e:
    print('Error during import:')
    traceback.print_exc()
