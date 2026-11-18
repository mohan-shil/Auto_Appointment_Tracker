const TERMINAL_STATES = new Set(["PAYMENT_REACHED", "STOPPED"]);

const TRANSITIONS = {
  IDLE: { START: "WAITING_FOR_LOGIN" },
  WAITING_FOR_LOGIN: { LOGIN_CONFIRMED: "AUTHENTICATED" },
  AUTHENTICATED: {
    PAUSE: "PAUSED",
    SESSION_EXPIRED: "PAUSED",
    PAYMENT_DETECTED: "PAYMENT_REACHED",
    UNEXPECTED_ERROR: "PAUSED"
  },
  PAUSED: {
    LOGIN_CONFIRMED: "AUTHENTICATED",
    RESUME: "AUTHENTICATED",
    STOP: "STOPPED"
  },
  PAYMENT_REACHED: { RESET: "IDLE" },
  STOPPED: { RESET: "IDLE" }
};

export function createWorkflowMachine() {
  let state = "IDLE";
  let pauseReason = null;
  let lastEvent = null;

  function snapshot() {
    return Object.freeze({ state, pauseReason, lastEvent });
  }

  function dispatch(event, details = {}) {
    if (typeof event !== "string") {
      return Object.freeze({ accepted: false, ...snapshot() });
    }

    if (event === "STOP" && !TERMINAL_STATES.has(state)) {
      state = "STOPPED";
      pauseReason = "Stopped by user";
      lastEvent = event;
      return Object.freeze({ accepted: true, ...snapshot() });
    }

    if (event === "RESUME" && state === "PAUSED" && details.sessionVerified !== true) {
      return Object.freeze({ accepted: false, ...snapshot() });
    }

    if (event === "RESET" && TERMINAL_STATES.has(state) && details.userConfirmed !== true) {
      return Object.freeze({ accepted: false, ...snapshot() });
    }

    const next = TRANSITIONS[state]?.[event];
    if (!next) {
      return Object.freeze({ accepted: false, ...snapshot() });
    }

    state = next;
    lastEvent = event;

    if (event === "SESSION_EXPIRED") {
      pauseReason = "Session expired; manual sign-in required";
    } else if (event === "UNEXPECTED_ERROR") {
      pauseReason = "Unexpected state; manual review required";
    } else if (event === "PAUSE") {
      pauseReason = "Paused by user";
    } else if (event === "PAYMENT_DETECTED") {
      pauseReason = "Payment page detected; automation stopped";
    } else if (event === "STOP") {
      pauseReason = "Stopped by user";
    } else {
      pauseReason = null;
    }

    return Object.freeze({ accepted: true, ...snapshot() });
  }

  return Object.freeze({ snapshot, dispatch });
}
