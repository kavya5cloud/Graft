from fastapi import FastAPI
import argparse, time

app=FastAPI(); MUTATE=None

def payload():
    x={"order_id":"ord_1001","customer":{"id":"cus_7","email":"a@example.com","phone":None},"total":"42.50","created_at":"2026-09-15T10:00:00Z","line_items":[{"sku":"A-1","price":"20.00","amount":"20.00"},{"sku":"B-2","price":"22.50","amount":"22.50"}],"shipping_address":{"city":"Ahmedabad","country":"IN"}}
    if MUTATE=="rename": x["grand_total"]=x.pop("total")
    elif MUTATE=="retype": x["total"]=42.5
    elif MUTATE=="drop": x.pop("shipping_address")
    elif MUTATE=="nest": x["summary"]={"total":x.pop("total")}
    return x
@app.get("/orders/1001")
def order(): return payload()

if __name__=="__main__":
    import uvicorn
    p=argparse.ArgumentParser(); p.add_argument("--mutate",choices=["rename","retype","drop","nest"]); p.add_argument("--port",type=int,default=8000); a=p.parse_args(); MUTATE=a.mutate; uvicorn.run(app,host="127.0.0.1",port=a.port)
