# Scrollbar native-input safety

The reported client termination has no recorded native crash stack or JavaScript
scrollbar exception in the available diagnostic logs. They stop after a result-page
request following a window resize. Unsupported cursor/CSS warnings are also present,
but do not establish the cause of the termination. No private diagnostic files or
game records are included in this repository.

The owned scrollbar now avoids host-sensitive operations during its input gesture:

- It never reads or calls DOM pointer-capture/release methods. Owned document
  listeners handle movement and release; blur, cancellation, teardown and a returning
  move with no left button held retire the gesture.
- Native presses do not programmatically focus the rail. Keyboard access remains
  available through its existing focusable scrollbar semantics; the browser preview
  retains ordinary click focus.
- Writing a scroll offset does not schedule a full window layout or native resize.
  Normal content-render and size-change paths still perform their required layout.
- Scroll notifications queue one edge check after the current input callback. Page
  loading waits until a held rail press/drag ends, so result construction cannot run
  synchronously inside that gesture. Replacement account/view/feed contexts and
  teardown invalidate queued work.
- Non-finite native coordinates or scroll offsets are rejected before reaching the
  native scroll setter.

`ui-scrollbar.cjs` exercises the shipped functions with throwing native-capture
adapters, a synchronous scroll setter, held/released gestures, coalesced work,
replacement-context ownership, invalid coordinates and teardown. Browser cases cover
track clicks and out-of-rail dragging at 100% and 200% scale without capture calls.
`ui-bidirectional-pages.cjs` checks that deferred edge handling retains its cleanup
ownership alongside continuous pagination.

These changes remove avoidable native capture and reentrant page-loading paths.
They are a defensive correction, not proof of the original native crash's cause.
A live-client check is still required to confirm that the reported termination no
longer occurs.
