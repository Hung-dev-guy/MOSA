"""Linear descriptor comparison for the local demo catalogue."""
import math


def rank(query,candidates):
    results=[]
    for product,vector in candidates:
        distance=math.sqrt(sum((a-b)**2 for a,b in zip(query,vector))/len(query))
        if distance<0.32:
            results.append({**product,'similarity':round(1-distance,4)})
    return sorted(results,key=lambda p:p['similarity'],reverse=True)
