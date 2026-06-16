import json
try:
    json.loads("['foo']")
except Exception as e:
    print("Single quotes:", str(e))
try:
    json.loads("")
except Exception as e:
    print("Empty string:", str(e))
try:
    json.loads("I cannot generate")
except Exception as e:
    print("Text:", str(e))
