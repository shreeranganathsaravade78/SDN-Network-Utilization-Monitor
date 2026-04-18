"""
Network Utilization Monitor - Ryu SDN Controller Application
============================================================
Collects OpenFlow port statistics every 5 seconds,
estimates bandwidth usage, and exposes data via REST API with CORS.
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from webob import Response
import time
import json





POLL_INTERVAL = 5  # seconds between each stats request (Time Intervel)





class NetworkMonitor(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(NetworkMonitor, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.port_stats = {}
        self.bandwidth = {}
        wsgi = kwargs['wsgi']
        wsgi.register(NetworkMonitorAPI, {'monitor_app': self})
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, ev):
        dp = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[dp.id] = dp
            self.logger.info("Switch CONNECTED: dpid=%s", dp.id)
        elif ev.state == DEAD_DISPATCHER:
            if dp.id in self.datapaths:
                del self.datapaths[dp.id]
                self.logger.info("Switch DISCONNECTED: dpid=%s", dp.id)

    def _monitor(self):
        while True:
            for dp in list(self.datapaths.values()):
                self._request_port_stats(dp)
            hub.sleep(POLL_INTERVAL)

    def _request_port_stats(self, dp):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        req = parser.OFPPortStatsRequest(dp, 0, ofp.OFPP_ANY)
        dp.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        dp_id = ev.msg.datapath.id
        now = time.time()
        for stat in ev.msg.body:
            port_no = stat.port_no
            rx_bytes = stat.rx_bytes
            tx_bytes = stat.tx_bytes
            key = (dp_id, port_no)
            if key in self.port_stats:
                prev_time, prev_rx, prev_tx = self.port_stats[key]
                delta_t = now - prev_time
                if delta_t > 0:
                    rx_mbps = (rx_bytes - prev_rx) * 8 / delta_t / 1_000_000
                    tx_mbps = (tx_bytes - prev_tx) * 8 / delta_t / 1_000_000
                    self.bandwidth[key] = (round(rx_mbps, 6), round(tx_mbps, 6))
                    self.logger.info(
                        "dpid=%-4s port=%-3s | RX: %8.4f Mbps | TX: %8.4f Mbps",
                        dp_id, port_no, rx_mbps, tx_mbps
                    )
            self.port_stats[key] = (now, rx_bytes, tx_bytes)


class NetworkMonitorAPI(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(NetworkMonitorAPI, self).__init__(req, link, data, **config)
        self.monitor_app = data['monitor_app']

    @route('monitor', '/stats/bandwidth', methods=['GET'])
    def get_bandwidth(self, req, **kwargs):
        result = {}
        try:
            for (dp_id, port_no), (rx, tx) in list(self.monitor_app.bandwidth.items()):
                label = "sw{}_port{}".format(dp_id, port_no)
                result[label] = {
                    "switch": dp_id,
                    "port": port_no,
                    "rx_mbps": rx,
                    "tx_mbps": tx
                }
        except Exception as e:
            result = {"error": str(e)}
        body = json.dumps(result, indent=2)
        resp = Response(content_type='application/json', charset='utf-8', text=body)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET'
        return resp

    @route('monitor', '/stats/switches', methods=['GET'])
    def get_switches(self, req, **kwargs):
        switches = list(self.monitor_app.datapaths.keys())
        body = json.dumps({"connected_switches": switches})
        resp = Response(content_type='application/json', charset='utf-8', text=body)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET'
        return resp
