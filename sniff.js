const { io } = require("socket.io-client");

const url = process.argv[2] || "http://localhost:3000";
const socket = io(url);

const emit = socket.emit.bind(socket);
socket.emit = function(ev, ...args) {
  console.log(">>>", ev, ...args);
  return emit(ev, ...args);
};

socket.onAny((ev, ...args) => console.log("<<<", ev, ...args));
socket.on("connect", () => console.log("--- connected", socket.id));
socket.on("disconnect", (reason) => console.log("--- disconnected", reason));
