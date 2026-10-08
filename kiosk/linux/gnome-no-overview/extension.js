import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

export default class NoOverview extends Extension {
    enable() {
        if (!Main.layoutManager._startingUp)
            return;
        Main.sessionMode.hasOverview = false;
        this._id = Main.layoutManager.connect('startup-complete', () => {
            Main.sessionMode.hasOverview = true;
        });
    }

    disable() {
        Main.sessionMode.hasOverview = true;
        if (this._id) {
            Main.layoutManager.disconnect(this._id);
            this._id = null;
        }
    }
}
