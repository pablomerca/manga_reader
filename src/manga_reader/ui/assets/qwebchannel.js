/****************************************************************************
 **
 ** Qt WebChannel JavaScript API
 **
 ** Copyright (C) 2016 The Qt Company Ltd.
 ** Copyright (C) 2016 basysKom GmbH
 **
 ** This file is part of the Qt WebChannel module of the Qt Toolkit.
 **
 ****************************************************************************/

"use strict";

var QWebChannelMessageTypes = {
    signal: 1,
    propertyUpdate: 2,
    init: 3,
    idle: 4,
    debug: 5,
    invokeMethod: 6,
    connectToSignal: 7,
    disconnectFromSignal: 8,
    setProperty: 9,
    response: 10,
};

class QWebChannel {
    constructor(transport, initCallback) {
        if (typeof transport !== "object" || typeof transport.send !== "function") {
            console.error("The QWebChannel expects a transport object with a send function and onmessage callback property." +
                " Given is: " + typeof transport);
            return;
        }

        var channel = this;
        this.transport = transport;

        this.send = function (data) {
            if (typeof (data) !== "string") {
                data = JSON.stringify(data);
            }
            channel.transport.send(data);
        };

        this.execCallbacks = {};
        this.execId = 0;
        this.exec = function (data, callback) {
            if (!callback) {
                // if no callback is given, send the message entirely asynchronously
                // regardless of the data.type
                channel.send(data);
                return;
            }

            if (channel.execId === Number.MAX_VALUE) {
                // wrap
                channel.execId = 0;
            }
            data.id = channel.execId;
            channel.execCallbacks[data.id] = callback;
            channel.execId++;
            channel.send(data);
        };

        this.objects = {};

        this.handleSignal = function (message) {
            var object = channel.objects[message.object];
            if (object) {
                object.signalEmitted(message.signal, message.args);
            } else {
                console.warn("Unhandled signal: " + message.object + "::" + message.signal);
            }
        };

        this.handleResponse = function (message) {
            if (!message.hasOwnProperty("id")) {
                console.error("Invalid response message received: ", JSON.stringify(message));
                return;
            }
            channel.execCallbacks[message.id](message.data);
            delete channel.execCallbacks[message.id];
        };

        this.handlePropertyUpdate = function (message) {
            for (var i in message.data) {
                var data = message.data[i];
                var object = channel.objects[data.object];
                if (object) {
                    object.propertyUpdate(data.signals, data.properties);
                } else {
                    console.warn("Unhandled property update: " + data.object + "::" + data.signal);
                }
            }
            channel.exec({ type: QWebChannelMessageTypes.idle });
        };

        this.debug = function (message) {
            channel.send({ type: QWebChannelMessageTypes.debug, data: message });
        };

        this.transport.onmessage = function (message) {
            var data = message.data;
            if (typeof data === "string") {
                data = JSON.parse(data);
            }
            switch (data.type) {
                case QWebChannelMessageTypes.signal:
                    channel.handleSignal(data);
                    break;
                case QWebChannelMessageTypes.response:
                    channel.handleResponse(data);
                    break;
                case QWebChannelMessageTypes.propertyUpdate:
                    channel.handlePropertyUpdate(data);
                    break;
                default:
                    console.error("Invalid message received: ", message.data);
                    break;
            }
        };

        this.exec({ type: QWebChannelMessageTypes.init }, function (data) {
            console.log("QWebChannel Init Data:", JSON.stringify(data));
            for (var objectName in data) {
                var object = new QObject(objectName, data[objectName], channel);
                channel.objects[objectName] = object;
            }
            if (initCallback) {
                initCallback(channel);
            }
        });
    }
}

class QObject {
    constructor(name, data, webChannel) {
        this.__id__ = name;
        this.webChannel = webChannel;

        for (var i in data.methods) {
            var method = data.methods[i];
            this[method[0]] = this.__createMethod(method[0], method[1]);
        }

        for (var i in data.properties) {
            var property = data.properties[i];
            this[property[0]] = property[1];
            this.__createProperty(property[0], property[1], property[2]);
        }

        for (var i in data.signals) {
            var signal = data.signals[i];
            this[signal[0]] = this.__createSignal(signal[0], signal[1]);
        }
    }
    __createMethod(methodName, args) {
        var object = this;
        return function () {
            var args = [];
            var callback = undefined;
            for (var i = 0; i < arguments.length; i++) {
                if (typeof arguments[i] === "function")
                    callback = arguments[i];

                else
                    args.push(arguments[i]);
            }
            object.webChannel.exec({
                "type": QWebChannelMessageTypes.invokeMethod,
                "object": object.__id__,
                "method": methodName,
                "args": args
            }, callback);
        };
    }
    __createProperty(name, value, signals) {
        var object = this;
        Object.defineProperty(object, name, {
            configurable: true,
            get: function () { return value; },
            set: function (newValue) {
                delete object[name];
                object[name] = newValue;
                object.__createProperty(name, newValue, signals);
                for (var i in signals) {
                    object[signals[i]](object[name]);
                }
                object.webChannel.exec({
                    "type": QWebChannelMessageTypes.setProperty,
                    "object": object.__id__,
                    "property": name,
                    "value": newValue
                });
            }
        });
    }
    __createSignal(name, args) {
        var object = this;
        var signal = function () {
            var callback = undefined;
            var args = [];
            for (var i = 0; i < arguments.length; i++) {
                if (typeof arguments[i] === "function")
                    callback = arguments[i];

                else
                    args.push(arguments[i]);
            }
            object.webChannel.exec({
                "type": QWebChannelMessageTypes.connectToSignal,
                "object": object.__id__,
                "signal": name,
                "args": args
            }, callback);
        };
        signal.connect = function (callback) {
            if (typeof (callback) !== "function") {
                console.error("Bad callback given to connect to signal " + name);
                return;
            }
            object.webChannel.exec({
                "type": QWebChannelMessageTypes.connectToSignal,
                "object": object.__id__,
                "signal": name
            }, function (data) {
                // Use the standard signal emission mechanism
                object[name] = function (args) {
                    callback.apply(callback, args);
                };
            });
        };
        signal.disconnect = function (callback) {
            object.webChannel.exec({
                "type": QWebChannelMessageTypes.disconnectFromSignal,
                "object": object.__id__,
                "signal": name
            });
        };
        return signal;
    }
    signalEmitted(signalName, signalArgs) {
        var signal = this[signalName];
        if (signal) {
            // Just invoke the function, the 'connect' wrapper handles the rest
            signal(signalArgs);
        } else {
            console.warn("Signal emitted but not found: " + signalName);
        }
    }
    propertyUpdate(signals, propertyMap) {
        for (var propertyName in propertyMap) {
            var value = propertyMap[propertyName];
            delete this[propertyName];
            this[propertyName] = value;
            this.__createProperty(propertyName, value, signals[propertyName]);
        }
    }
}






