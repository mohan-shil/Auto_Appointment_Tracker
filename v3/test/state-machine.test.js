import test from "node:test";
import assert from "node:assert/strict";
import { createWorkflowMachine } from "../src/workflow/state-machine.js";

test("workflow requires a start and a user-confirmed login before authenticated state", () => {
  const machine = createWorkflowMachine();
  assert.equal(machine.snapshot().state, "IDLE");
  assert.equal(machine.dispatch("LOGIN_CONFIRMED").accepted, false);
  assert.equal(machine.dispatch("START").state, "WAITING_FOR_LOGIN");
  assert.equal(machine.dispatch("LOGIN_CONFIRMED").state, "AUTHENTICATED");
});

test("expired sessions pause and require manual login before resuming", () => {
  const machine = createWorkflowMachine();
  machine.dispatch("START");
  machine.dispatch("LOGIN_CONFIRMED");
  const paused = machine.dispatch("SESSION_EXPIRED");
  assert.equal(paused.state, "PAUSED");
  assert.match(paused.pauseReason, /manual sign-in required/);
  assert.equal(machine.dispatch("RESUME", { sessionVerified: true }).accepted, false);
  assert.equal(machine.dispatch("LOGIN_CONFIRMED").state, "AUTHENTICATED");
});

test("resume from a user pause requires an explicitly verified session", () => {
  const machine = createWorkflowMachine();
  machine.dispatch("START");
  machine.dispatch("LOGIN_CONFIRMED");
  machine.dispatch("PAUSE");
  assert.equal(machine.dispatch("RESUME").accepted, false);
  assert.equal(machine.dispatch("RESUME", { sessionVerified: true }).state, "AUTHENTICATED");
});

test("payment detection stops the workflow and requires explicit reset confirmation", () => {
  const machine = createWorkflowMachine();
  machine.dispatch("START");
  machine.dispatch("LOGIN_CONFIRMED");
  const result = machine.dispatch("PAYMENT_DETECTED");
  assert.equal(result.state, "PAYMENT_REACHED");
  assert.match(result.pauseReason, /automation stopped/);
  assert.equal(machine.dispatch("START").accepted, false);
  assert.equal(machine.dispatch("RESET").accepted, false);
  assert.equal(machine.dispatch("RESET", { userConfirmed: true }).state, "IDLE");
});

test("unexpected states pause for manual review without automatic retry", () => {
  const machine = createWorkflowMachine();
  machine.dispatch("START");
  machine.dispatch("LOGIN_CONFIRMED");
  const result = machine.dispatch("UNEXPECTED_ERROR");
  assert.equal(result.state, "PAUSED");
  assert.match(result.pauseReason, /manual review required/);
});

test("user stop is terminal until explicitly reset", () => {
  const machine = createWorkflowMachine();
  machine.dispatch("START");
  const stopped = machine.dispatch("STOP");
  assert.equal(stopped.state, "STOPPED");
  assert.equal(machine.dispatch("LOGIN_CONFIRMED").accepted, false);
  assert.equal(machine.dispatch("RESET", { userConfirmed: true }).state, "IDLE");
});

test("snapshots are immutable and do not expose mutable internal state", () => {
  const machine = createWorkflowMachine();
  const state = machine.snapshot();
  assert.equal(Object.isFrozen(state), true);
  assert.throws(() => { state.state = "AUTHENTICATED"; }, TypeError);
  assert.equal(machine.snapshot().state, "IDLE");
});
