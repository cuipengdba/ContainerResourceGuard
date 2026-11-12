"""One owned loopback HTTP connection, no raw payload saved."""
import http.client,json,socket,time
r={'schema':'crg-loopback-transport-v1','started_monotonic_ns':time.monotonic_ns(),'request_ok':False,'pre_request_hold_seconds':0,'socket_timeout_seconds':4}
try:
 c=http.client.HTTPConnection('127.0.0.1',8090,timeout=4);c.connect();r.update(local_port=c.sock.getsockname()[1],server_port=c.sock.getpeername()[1])
 c.putrequest('POST','/test');c.putheader('Content-Type','application/json');c.putheader('Content-Length','2');c.endheaders(b'{}')
 response=c.getresponse();r['request_ok']=response.status==200 and json.loads(response.read(1024)).get('Result')=='000';c.close()
except Exception as e:r['error_class']=type(e).__name__
r['finished_monotonic_ns']=time.monotonic_ns();print(json.dumps(r));raise SystemExit(0 if r['request_ok'] else 1)
