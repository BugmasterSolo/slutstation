const express = require("express");
const app = express();
const ws = require("ws");
const http = require("http");
const url = require("url");
// const session = require("express-session");

const server = http.createServer(app);

app.use(express.static('public'));

const TICK = 32;

const POLLRATE = 1000 / TICK;

setInterval(broadcastData, POLLRATE);

const connectionCache = new Map();

function broadcastData() {
    let length = connectionCache.size;
    let buffer = new Uint32Array(length);
    let cur = 0;
    for (let conn of connectionCache) {
        buffer[cur] = conn.data
    }

    for (let conn of connectionCache) {
        conn.broadcast(buffer);
        // handle pruning process later
        // also: use more predictable PIDs and send them back/forth via cookies probably (or sessions???)
    }
}


// add intervals to the event tracker (likely a map)
// on tick, broadcast state to all of them
// can be removed

class ConnectionInstance {
    constructor(ws) {
        this.ws = ws;
        this.pid = Math.random() * Number.MAX_SAFE_INTEGER;  // pass to sessions in the future
        // please don't overlap any time soon
        ws.on("message", this.updateCache);
        ws.on("close", this.clearConnection);
        connectionCache.set(this.pid, this);
        this.data = 0;
    }

    updateCache(data) {
        console.log(data);
        this.data = data;
    }

    broadcast(data) {
        ws.send(data);
    }

    clearConnection() {
        connectionCache.delete(this.pid);
        ws.removeEventListener("message", this.updateCache);
        ws.removeEventListener("close", this.clearConnection);
        clearInterval(this.timer);
    }
};


wspos = ws.Server( {
    noServer: true
} );

server.on("upgrade", (req, socket, head) => {
    const path = url.parse(req.url).pathname;
    console.log(path);

    if (path === "/gp") {
        wspos.emit("connection", socket);
    }
});

wspos.on("connection", ws => {
    let conn = new ConnectionInstance(ws);
    connectionCache.set(conn.pid, conn);
});

// make a js page which simply communicates with the server
// buffer can consist of 32 bit ints (10 bit x, 10 bit y, 12 bit color)

// const server = http.createServer(app);

// app.use(function(req, res, next) {
//     res.setHeader("Content-Security-Policy", "default-src 'self'; img-src 'self'")
//     next();
// })

// app.use(express.static('public'));

// wsServer = new ws.Server({
//     server: server
// });

// wsServer.on("connection", (ws) => {
//     ws.on("message", (msg) => {
//         console.log(msg);
//         ws.send("doy doy");
//     });
// });

// server.listen(8000, function() {
//     console.log("hello moto");
// })

