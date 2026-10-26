/**
 * Creates an observer for a specific model within subViews.
 * This observer provides a subscription mechanism for data change notifications.
 *
 * @param {string} [featureName] - The name of the feature model to observe. If not provided, the observer will target the main window model.
 * @returns {{
 *   resId: number|null,
 *   model: object|null,
 *   subscribe: function(): void,
 *   unsubscribe: function(): void,
 *   onUpdate: function(function(object): void): void
 * }}
 */
const ModelObserver = (featureName) => {
    const context = {
        resId: 0, // Root model by default use 0
        callbackId: null,
        onUpdateCallbacks: [],

        /**
         * Subscribes to model change events in the game engine.
         */
        subscribe() {
            if (this._boundOnDataChanged)
                return;
            this._boundOnDataChanged = this.onDataChanged.bind(this);
            engine.on("viewEnv.onDataChanged", this._boundOnDataChanged);
            this.callbackId = viewEnv.addDataChangedCallback(
                "model",
                this.resId,
                true,
            );
        },

        /**
         * Unsubscribes from model change events.
         */
        unsubscribe() {
            if (this._boundOnDataChanged) {
                engine.off("viewEnv.onDataChanged", this._boundOnDataChanged);
                this._boundOnDataChanged = null;
            }
            if (this.callbackId) {
                viewEnv.removeDataChangedCallback(this.callbackId, this.resId);
                this.callbackId = null;
            }
        },

        /**
         * Retrieves the observed model object.
         * @returns {object|null} The model if found; otherwise, null.
         */
        get model() {
            return this.resId
                ? window.subViews.get(this.resId)?.model
                : window.model;
        },

        /**
         * Registers a callback that fires when the model changes.
         * @param {function(object): void} callback - The function to call with the updated model.
         */
        onUpdate(callback) {
            this.onUpdateCallbacks.push(callback);
        },

        /**
         * Internal handler for the engine's `viewEnv.onDataChanged` event.
         * The event is broadcast for every tracked model in the view, so the
         * handler only reacts when its own `callbackId` is among `callbackIDs`
         * and then notifies subscribers via {@link notifyUpdate}.
         *
         * @param {any} data - Snapshot of the changed model data sent from the view model on Python side.
         * @param {any} indexes - Indexes of changed sub-items when array properties are tracked (`trackSubItems`); unused here.
         * @param {number[]} callbackIDs - IDs returned by `viewEnv.addDataChangedCallback` for the callbacks affected by this change.
         * @private
         */
        onDataChanged(data, indexes, callbackIDs) {
            if (callbackIDs.includes(this.callbackId)) {
                this.notifyUpdate();
            }
        },

        /**
         * Notifies all registered callbacks with the current model.
         * @private
         */
        notifyUpdate() {
            for (const cb of this.onUpdateCallbacks) {
                cb(this.model);
            }
        },
    };

    // If a feature name is provided, we want use subView model
    // find the corresponding resId for it when the engine is ready.
    if (featureName) {
        engine.whenReady.then(() => {
            for (const resId of window.subViews.ids()) {
                const modModel =
                    window.subViews.get(resId)?.model?.ModInjectModel;
                if (modModel && modModel.name === featureName) {
                    context.resId = resId;
                    break;
                }
            }
        });
    }

    return context;
};

// Export public functions and constants
export { ModelObserver };
