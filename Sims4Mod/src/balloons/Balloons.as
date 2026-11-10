package s4ai.boot



{



   import flash.display.MovieClip;



   import flash.display.Shape;



   import flash.display.Sprite;



   import flash.display.DisplayObject;



   import flash.display.DisplayObjectContainer;



   import flash.events.Event;



   import flash.external.ExternalInterface;



   import flash.filters.DropShadowFilter;



   import flash.geom.Matrix;



   import flash.geom.Rectangle;



   import flash.display.GradientType;



   import flash.text.TextField;



   import flash.text.TextFieldAutoSize;



   import flash.text.TextFormat;



   import flash.utils.Dictionary;



   import flash.utils.ByteArray;



import flash.utils.getDefinitionByName;



   import flash.utils.getTimer;



   import flash.utils.setTimeout;



   [SWF(width="1024", height="768", frameRate="30")]



   public class Boot extends Sprite



   {



      private static const SLOT:String = "FacebookDisplay";



      private static const CMD_SHOW:String = "ui.synapse_balloon";



      private static const CMD_CLEAR:String = "ui.synapse_balloon_clear";



      private static const CMD_BOOT:String = "ui.synapse_boot";



      private static const SERVER_READY:String = "synapse.ui_ready";



      private static const SERVER_LOG:String = "synapse.ui_log";



      public static var sActiveInstance:Boot = null;



      public var widget:Object;



      private var balloonLayer:Sprite = new Sprite();



      private var activeBalloons:Dictionary = new Dictionary();



      private var isStarted:Boolean = false;



      public var settingsUI:Object;



      private var instanceId:int = 0;



       public static var sBalloonStyle:Object = {



          scale_pct: 100,



          max_width: 260,



          font_size: 15,



          leading: 4,



          show_name: true,



          name_font_size: 11,



          pad_x: 16,



          pad_y: 13,



          radius: 15,



          offset_y: 32,



          offset_x: 0,



          camera_scale: true,



          min_scale_pct: 35,



          bg_alpha_pct: 98,



          theme: "light",



          type_speed: 35,



          duration_pct: 100



       };



       public static var sStudioTargetSimId:String = "0";



       public static var sStudioTargetSimName:String = "";



       public static var sStudioPreviewData:Object = null;



       public var studioUI:Object = null;



      public function Boot()



      {



         super();



         this.instanceId = int(Math.random() * 90000) + 10000;



         mouseEnabled = false;



         mouseChildren = false;



         this.balloonLayer.mouseEnabled = false;



         this.balloonLayer.mouseChildren = false;



         this.addChild(this.balloonLayer);



         // Clean up any previously active instance across zone/CAS transitions



         if(sActiveInstance != null && sActiveInstance != this)



         {



            try



            {



               sActiveInstance.cleanup();



            }



            catch(e_old:Error) {}



         }



         sActiveInstance = this;



         try



         {



            var wb:Class = getDefinitionByName("olympus.core.widget.WidgetBase") as Class;



            this.widget = new wb();



            this.widget.mcPositionHelper = new MovieClip();



            this.widget.bIsModal = false;



            this.widget.isModal = false;



         }



         catch(e:Error) {}



         this.registerDebugCommands();



         this.releaseModality();



         this.logToServer("Boot init: id=" + this.instanceId);



         addEventListener(Event.ADDED_TO_STAGE, this.onAdded, false, 0, true);



         addEventListener(Event.REMOVED_FROM_STAGE, this.onRemoved, false, 0, true);



      }



      private static function staticOnShowCommand(args:Array, params:Object, ctx:String):void



      {



         if(sActiveInstance != null)



         {



            sActiveInstance.onShowCommand(args, params, ctx);



         }



      }



      private static function staticOnClearCommand(args:Array, params:Object, ctx:String):void



      {



         if(sActiveInstance != null)



         {



            sActiveInstance.onClearCommand(args, params, ctx);



         }



      }



      private static function staticOnBootCommand(args:Array, params:Object, ctx:String):void



      {



         if(sActiveInstance != null)



         {



            sActiveInstance.onBootCommand(args, params, ctx);



         }



      }



      private function registerDebugCommands():void



      {



         try



         {



            var dbgClass:Class = getDefinitionByName("olympus.io.DebugCommands") as Class;



            if(dbgClass)



            {



               try { dbgClass["Unregister"](CMD_SHOW); } catch(u1:Error) {}



               try { dbgClass["Unregister"](CMD_CLEAR); } catch(u2:Error) {}



               try { dbgClass["Unregister"](CMD_BOOT); } catch(u3:Error) {}



               dbgClass["Register"](CMD_SHOW, staticOnShowCommand, "Show Synapse AI Balloon", "simId [type] name text duration");



               dbgClass["Register"](CMD_CLEAR, staticOnClearCommand, "Clear Synapse AI Balloons", "");



               dbgClass["Register"](CMD_BOOT, staticOnBootCommand, "Wake up Synapse AI Balloons", "");



               try { dbgClass["Unregister"]("ui.synapse_settings"); } catch(e1:Error) {}



               try { dbgClass["Unregister"]("synapse.open_settings"); } catch(e2:Error) {}



               try { dbgClass["Unregister"]("synapse.settings"); } catch(e3:Error) {}



               try { dbgClass["Unregister"]("ui.synapse_settings_lore"); } catch(e4:Error) {}



               try { dbgClass["Unregister"]("ui.synapse_lore_saved"); } catch(e5:Error) {}



               try { dbgClass["Unregister"]("ui.synapse_lore_cleared"); } catch(e6:Error) {}



               dbgClass["Register"]("ui.synapse_settings", staticOnSettingsCommand, "Synapse Settings UI", "");



               dbgClass["Register"]("synapse.open_settings", staticOnSettingsCommand, "Synapse Settings UI", "");



               dbgClass["Register"]("synapse.settings", staticOnSettingsCommand, "Synapse Settings UI", "");



               dbgClass["Register"]("ui.synapse_settings_lore", staticOnLoreDataCommand, "Synapse Lore Data", "");



               dbgClass["Register"]("ui.synapse_lore_saved", staticOnLoreSavedCommand, "Synapse Lore Saved Ack", "");



               dbgClass["Register"]("ui.synapse_lore_cleared", staticOnLoreClearedCommand, "Synapse Lore Cleared Ack", "");



               try { dbgClass["Unregister"]("ui.synapse_balloon_style"); } catch(eBs1:Error) {}



               try { dbgClass["Unregister"]("ui.synapse_studio_start"); } catch(eSs1:Error) {}



               try { dbgClass["Unregister"]("ui.synapse_studio_stop"); } catch(eSs2:Error) {}



               dbgClass["Register"]("ui.synapse_balloon_style", staticOnBalloonStyleCommand, "Synapse Balloon Style Data", "");



               dbgClass["Register"]("ui.synapse_studio_start", staticOnStudioStartCommand, "Synapse Balloon Studio Start", "");



               dbgClass["Register"]("ui.synapse_studio_stop", staticOnStudioStopCommand, "Synapse Balloon Studio Stop", "");



               // Direct map override if accessible



               try



               {



                  var sInst:Object = dbgClass["sInstance"];



                  if(sInst && sInst["mCommandMap"])



                  {



                     sInst["mCommandMap"][CMD_SHOW] = staticOnShowCommand;



                     sInst["mCommandMap"][CMD_CLEAR] = staticOnClearCommand;



                     sInst["mCommandMap"][CMD_BOOT] = staticOnBootCommand;



                     sInst["mCommandMap"]["ui.synapse_settings"] = staticOnSettingsCommand;



                     sInst["mCommandMap"]["synapse.open_settings"] = staticOnSettingsCommand;



                     sInst["mCommandMap"]["synapse.settings"] = staticOnSettingsCommand;



                     sInst["mCommandMap"]["ui.synapse_settings_lore"] = staticOnLoreDataCommand;



                     sInst["mCommandMap"]["ui.synapse_lore_saved"] = staticOnLoreSavedCommand;



                     sInst["mCommandMap"]["ui.synapse_lore_cleared"] = staticOnLoreClearedCommand;



                     sInst["mCommandMap"]["ui.synapse_balloon_style"] = staticOnBalloonStyleCommand;



                     sInst["mCommandMap"]["ui.synapse_studio_start"] = staticOnStudioStartCommand;



                     sInst["mCommandMap"]["ui.synapse_studio_stop"] = staticOnStudioStopCommand;



                  }



               }



               catch(eMap:Error) {}



            }



         }



         catch(e2:Error) {}



      }



      public function cleanup():void



      {



         this.onClearCommand(null, null, "");



         try



         {



            this.balloonLayer.removeEventListener(Event.ENTER_FRAME, this.onEnterFrame);



         }



         catch(e_ef:Error) {}



         if(this.balloonLayer && this.balloonLayer.parent)



         {



            try



            {



               this.balloonLayer.parent.removeChild(this.balloonLayer);



            }



            catch(e_rem:Error) {}



         }



      }



      private function onRemoved(e:Event):void



      {



         if(sActiveInstance == this)



         {



            this.cleanup();



         }



      }



      private function attachBalloonLayer():void



      {



         var target:DisplayObjectContainer = null;



         try



         {



            var cm:Object = getDefinitionByName("olympus.io.CommunicationManager");



            // Layer 8: WORLD_ELEMENTS (The official persistent 3D elements layer in Sims 4)



            target = cm.CallUIService("GetLayer", {"layer": 8}) as DisplayObjectContainer;



            if(!target)



            {



               // Fallback: Layer 1 (ALWAYS_ON_TOP_NO_INPUT)



               target = cm.CallUIService("GetLayer", {"layer": 1}) as DisplayObjectContainer;



            }



         }



         catch(e_layer:Error) {}



         if(!target && stage)



         {



            target = stage;



         }



         if(target)



         {



            if(this.balloonLayer.parent && this.balloonLayer.parent != target)



            {



               try



               {



                  this.balloonLayer.parent.removeChild(this.balloonLayer);



               }



               catch(e_rem:Error) {}



            }



            if(!this.balloonLayer.parent)



            {



               target.addChild(this.balloonLayer);



            }



         }



         else if(!this.balloonLayer.parent)



         {



            this.addChild(this.balloonLayer);



         }



         // Ensure balloonLayer itself ticks onEnterFrame so animation never stops



         try



         {



            this.balloonLayer.removeEventListener(Event.ENTER_FRAME, this.onEnterFrame);



            this.balloonLayer.addEventListener(Event.ENTER_FRAME, this.onEnterFrame);



         }



         catch(e_ef:Error) {}



      }



      private function onAdded(e:Event):void



      {



         sActiveInstance = this;



         this.registerDebugCommands();



         this.attachBalloonLayer();



         if(!this.isStarted)



         {



            this.isStarted = true;



            try



            {



               getDefinitionByName("olympus.io.CommunicationManager").AddMessageListenerByName("Show" + SLOT, this.onReshow, "SynapseBalloons");



            }



            catch(err:Error) {}



         }



         this.releaseModality();



         setTimeout(this.releaseModality, 250);



         this.logToServer("onAdded: id=" + this.instanceId + ", hasStage=" + (stage != null) + ", layerParent=" + (this.balloonLayer.parent != null));



         // Notify Python that Flash UI is ready



         try



         {



            ExternalInterface.call("CallGameService", "PostServerCommand", {



               "command": SERVER_READY,



               "commandArgs": []



            }, false);



         }



         catch(e3:Error) {}



      }



            private static function staticOnSettingsCommand(args:Array, params:Object, ctx:String):void



      {



         if(sActiveInstance != null)



         {



            sActiveInstance.onSettingsCommand(args, params, ctx);



         }



      }



      private static function staticOnLoreDataCommand(args:Array, params:Object, ctx:String):void



      {



         if(sActiveInstance != null)



         {



            try



            {



               if(sActiveInstance.settingsUI == null)



               {



                  sActiveInstance.settingsUI = new SettingsUI();



                  if(sActiveInstance.stage)



                  {



                     sActiveInstance.stage.addChild(sActiveInstance.settingsUI as Sprite);



                  }



               }



               if(sActiveInstance.settingsUI != null)



               {



                  sActiveInstance.settingsUI.onLoreDataCommand(args);



               }



            }



            catch(eLD:Error)



            {



               sActiveInstance.logToServer("staticOnLoreDataCommand ERR: " + eLD.message);



            }



         }



      }



      private static function staticOnLoreSavedCommand(args:Array, params:Object, ctx:String):void



      {



         if(sActiveInstance != null && sActiveInstance.settingsUI != null)



         {



            sActiveInstance.settingsUI.onLoreSavedCommand(args);



         }



      }



      private static function staticOnLoreClearedCommand(args:Array, params:Object, ctx:String):void



      {



         if(sActiveInstance != null && sActiveInstance.settingsUI != null)



         {



            sActiveInstance.settingsUI.onLoreClearedCommand(args);



         }



      }



      public function onSettingsCommand(args:Array, params:Object, ctx:String):void



      {



         try



         {



            if(this.settingsUI == null)



            {



               this.settingsUI = new SettingsUI();



            }



            if(this.settingsUI != null)



            {



               if((this.settingsUI as Sprite).parent == null)



               {



                  if(stage)



                  {



                     stage.addChild(this.settingsUI as Sprite);



                  }



                  else if(this.balloonLayer && this.balloonLayer.parent)



                  {



                     this.balloonLayer.parent.addChild(this.settingsUI as Sprite);



                  }



                  else



                  {



                     this.addChild(this.settingsUI as Sprite);



                  }



               }



               this.settingsUI.handleSettingsCommand(args);



               this.logToServer("onSettingsCommand OK: args=" + (args ? args.join(",") : "") + ", visible=" + this.settingsUI.visible);



            }



         }



         catch(errSet:Error)



         {



            this.logToServer("onSettingsCommand ERR: " + errSet.message);



         }



      }



      private function releaseModality():void



      {



         try



         {



            var cm:Object = getDefinitionByName("olympus.io.CommunicationManager");



            cm.SendUIMessage("HideComplete" + SLOT, null);



            cm.CallUIService("SetWidgetModality", {



               "widgetName": SLOT,



               "bOn": false



            });



         }



         catch(e:Error) {}



      }



      private function onBootCommand(args:Array, params:Object, ctx:String):void



      {



         this.logToServer("onBootCommand: id=" + this.instanceId);



         this.onReshow(null);



      }



      private function onReshow(data:Object):void



      {



         sActiveInstance = this;



         this.onClearCommand(null, null, "");



         this.registerDebugCommands();



         this.attachBalloonLayer();



         this.releaseModality();



         setTimeout(this.releaseModality, 250);



         try



         {



            ExternalInterface.call("CallGameService", "PostServerCommand", {



               "command": SERVER_READY,



               "commandArgs": []



            }, false);



         }



         catch(e3:Error) {}



      }



      private function onClearCommand(args:Array, params:Object, ctx:String):void



      {



         for(var key:* in this.activeBalloons)



         {



            var b:Object = this.activeBalloons[key];



            if(b)



            {



               this.removeBalloon(b);



            }



         }



         this.activeBalloons = new Dictionary();



      }



      public static function sendServerLog(msg:String):void

      {

         try

         {

            ExternalInterface.call("CallGameService", "PostServerCommand", {

               "command": SERVER_LOG,

               "commandArgs": [encodeURIComponent(msg)]

            }, false);

         }

         catch(e:Error) {}

      }



      public function logToServer(msg:String):void

      {

         Boot.sendServerLog(msg);

      }



      private function decodeSafe(s:String):String



      {



         if(!s) return "";



         try



         {



            return decodeURIComponent(s);



         }



         catch(e:Error)



         {



            return s;



         }



         return s;



      }



      private function onShowCommand(args:Array, params:Object, ctx:String):void



      {



         if(!args || args.length < 1)



         {



            return;



         }



         var simId:String = String(args[0]);



         var balloonType:String = "speech";



         var idx:int = 1;



         if(args.length > 2 && (String(args[1]) == "speech" || String(args[1]) == "thought"))



         {



            balloonType = String(args[1]);



            idx = 2;



         }



         var simName:String = args.length > idx ? this.decodeSafe(String(args[idx])) : "";



         idx++;



         var text:String = args.length > idx ? this.decodeSafe(String(args[idx])) : "Привет!";



         idx++;



         var duration:Number = args.length > idx ? Number(args[idx]) : 6.0;



         if(isNaN(duration) || duration <= 0)



         {



            duration = 6.0;



         }



         idx++;



         var colorTop:uint = args.length > idx ? uint(args[idx]) : 0;



         idx++;



         var colorBot:uint = args.length > idx ? uint(args[idx]) : 0;



         this.logToServer("onShow: id=" + this.instanceId + ", sim=" + simId + ", text=" + text.substr(0, 15));



         this.createBalloon(simId, balloonType, simName, text, duration, colorTop, colorBot);



      }



      private static function staticOnBalloonStyleCommand(args:Array, params:Object, ctx:String):void



      {



         if(sActiveInstance != null && args && args.length > 0)



         {



            sActiveInstance.applyBalloonStyle(String(args[0]));



         }



      }



      private static function staticOnStudioStartCommand(args:Array, params:Object, ctx:String):void



      {



         if(sActiveInstance != null)



         {



            var sId:String = (args && args.length > 0) ? String(args[0]) : "0";



            var sNm:String = (args && args.length > 1) ? sActiveInstance.decodeSafe(String(args[1])) : "Сим";



            sActiveInstance.onStudioStartCommand(sId, sNm);



         }



      }



      private static function staticOnStudioStopCommand(args:Array, params:Object, ctx:String):void



      {



         if(sActiveInstance != null)



         {



            sActiveInstance.onStudioStopCommand();



         }



      }



      public function applyBalloonStyle(styleStr:String):void



      {



         if(!styleStr) return;



         var pairs:Array = styleStr.split(";");



         for(var i:int = 0; i < pairs.length; i++)



         {



            var item:String = String(pairs[i]);



            var kv:Array = item.split(":");



            if(kv.length == 2)



            {



               var k:String = String(kv[0]);



               var v:String = String(kv[1]);



               if(k == "show_name" || k == "camera_scale")



               {



                  sBalloonStyle[k] = (v == "1");



               }



               else if(k == "theme")



               {



                  sBalloonStyle[k] = v;



               }



               else



               {



                  var n:Number = Number(v);



                  if(!isNaN(n))



                  {



                     sBalloonStyle[k] = n;



                  }



               }



            }



         }



         this.logToServer("applyBalloonStyle OK: scale=" + sBalloonStyle.scale_pct + ", w=" + sBalloonStyle.max_width);



      }



      public function rebindBalloon(b:Object):void



      {



         if(!b || !b.balloon || !b.simId) return;



         var offY:Number = Number(sBalloonStyle.offset_y || 32) / 100.0;



         var offX:Number = Number(sBalloonStyle.offset_x || 0) / 100.0;



         var camScale:Boolean = (sBalloonStyle.camera_scale !== false);



         var minSc:Number = Number(sBalloonStyle.min_scale_pct || 35) / 100.0;



         try



         {



            ExternalInterface.call("CallGameService", "BindDisplayObject", {



               "displayObject": b.balloon,



               "objectId": b.simId,



               "attachPoint": "b__Head__",



               "worldOffset": {



                  "x": offX,



                  "y": offY,



                  "z": 0



               },



               "viewOffset": {



                  "x": 0,



                  "y": 0,



                  "z": 0



               },



               "screenOffset": {



                  "x": 0,



                  "y": 0,



                  "z": -0.2



               },



               "isOccludedByWorld": false,



               "isScaledByCamera": camScale,



               "minScale": minSc,



               "maxVisibleScale": 0,



               "lockVisibility": false,



               "lockToScreenEdge": false,



               "lockToScreenEdgeScale": {



                  "mTop": 1,



                  "mBottom": 1,



                  "mBot": 1,



                  "mLeft": 1,



                  "mRight": 1



               },



               "adjustScreenPositionForMargin": false



            }, false);



         }



         catch(e:Error) {}



      }



      public static function showStudioPreviewBalloon(simId:String, simName:String, text:String, bType:String):void

      {

         if(sActiveInstance == null) return;

         Boot.clearStudioPreviewBalloon();

         sActiveInstance.createBalloon(simId, bType, simName, text, 999999.0);

         var b:Object = sActiveInstance.activeBalloons[simId];

         if(b != null)

         {

            b.isPinned = true;

            b.state = "holding";

            b.typedChars = text.length;

            if(b.tf != null)

            {

               (b.tf as TextField).text = text;

            }

            var curTextW:Number = Math.ceil((b.tf as TextField).textWidth) + 8;

            var curTextH:Number = Math.ceil((b.tf as TextField).textHeight);

            if(curTextH < 22) curTextH = 22;

            var contentW:Number = Math.max(curTextW, b.hasName ? b.nameW : 0);

            b.currentBoxW = Math.max(b.minBoxW, contentW + b.padX * 2);

            b.currentBoxH = curTextH + b.padY * 2 + (b.hasName ? b.nameH + 7 : 0) + 6;

            b.targetBoxW = b.currentBoxW;

            b.targetBoxH = b.currentBoxH;

            if(b.body != null)

            {

               b.body.alpha = 1.0;

               var sc:Number = Number(sBalloonStyle.scale_pct || 100) / 100.0;

               b.body.scaleX = sc;

               b.body.scaleY = sc;

            }

            sStudioPreviewData = b;

            sActiveInstance.redrawBalloon(b);

         }

      }



      public static function updateStudioPreview(text:String, bType:String):void

      {

         if(sActiveInstance == null || sStudioPreviewData == null) return;

         var b:Object = sStudioPreviewData;

         Boot.showStudioPreviewBalloon(String(b.simId), String(b.simName), text, bType);

      }



      public static function clearStudioPreviewBalloon():void

      {

         if(sActiveInstance == null) return;

         if(sStudioPreviewData != null)

         {

            sActiveInstance.removeBalloon(sStudioPreviewData);

            sStudioPreviewData = null;

         }

      }



      public static function replayStudioPreviewAnimation():void

      {

         if(sActiveInstance == null || sStudioPreviewData == null) return;

         var b:Object = sStudioPreviewData;

         b.state = "opening";

         b.stateTime = getTimer();

         b.startTime = getTimer();

         b.typedChars = 0;

         if(b.tf != null)

         {

            (b.tf as TextField).text = "";

         }

         b.currentBoxW = Math.max(b.minBoxW, (b.hasName ? b.nameW : 24) + b.padX * 2);

         b.currentBoxH = 22 + b.padY * 2 + (b.hasName ? b.nameH + 7 : 0) + 6;

         b.targetBoxW = b.currentBoxW;

         b.targetBoxH = b.currentBoxH;

         sActiveInstance.redrawBalloon(b);

      }



      public function onStudioStartCommand(simId:String, simName:String):void



      {



         sStudioTargetSimId = simId;



         sStudioTargetSimName = simName;



         if(this.settingsUI != null)



         {



            (this.settingsUI as SettingsUI).onStudioStartFromPython(simId, simName);



         }



      }



      public function onStudioStopCommand():void



      {



         clearStudioPreviewBalloon();



         if(this.settingsUI != null)



         {



            (this.settingsUI as SettingsUI).hideStudioPanel();



         }



      }



      private function createBalloon(simId:String, balloonType:String, simName:String, text:String, durationSec:Number, colorTop:uint = 0, colorBot:uint = 0):void



      {



         this.attachBalloonLayer();



         if(this.activeBalloons[simId])



         {



            this.removeBalloon(this.activeBalloons[simId]);



         }



         var balloon:Sprite = new Sprite();



         balloon.mouseEnabled = false;



         balloon.mouseChildren = false;



         var body:Sprite = new Sprite();



         body.mouseEnabled = false;



         body.mouseChildren = false;



         balloon.addChild(body);



         var isThought:Boolean = (balloonType == "thought");



         var maxTextWidth:Number = Number(sBalloonStyle.max_width || 260);



         var padX:Number = Number(sBalloonStyle.pad_x || 16);



         var padY:Number = Number(sBalloonStyle.pad_y || 13);



         var radius:Number = isThought ? (Number(sBalloonStyle.radius || 15) + 3) : Number(sBalloonStyle.radius || 15);



         // Text field with Scaleform embedded font



         var tf:TextField = new TextField();



         tf.multiline = true;



         tf.wordWrap = true;



         tf.autoSize = TextFieldAutoSize.LEFT;



         tf.selectable = false;



         tf.mouseEnabled = false;



         tf.embedFonts = true;



         var textThemeColor:uint = (sBalloonStyle.theme == "dark") ? 0xF0F3F8 : ((sBalloonStyle.theme == "warm") ? 0x2C221A : 0x1E1E24);



         var fmt:TextFormat = new TextFormat("$TextFont", Number(sBalloonStyle.font_size || 15), textThemeColor);



         fmt.leading = Number(sBalloonStyle.leading || 4);



         tf.defaultTextFormat = fmt;



         tf.width = maxTextWidth;



         tf.text = "";



         var hasName:Boolean = simName != null && simName.length > 0 && simName != "null" && (sBalloonStyle.show_name !== false);



         var nameSprite:Sprite = new Sprite();



         var nameH:Number = 0;



         var nameW:Number = 0;



         if(hasName)



         {



            var ntf:TextField = new TextField();



            ntf.autoSize = TextFieldAutoSize.LEFT;



            ntf.selectable = false;



            ntf.mouseEnabled = false;



            ntf.embedFonts = true;



            var nfmt:TextFormat = new TextFormat("$BoldHeadlineFont", Number(sBalloonStyle.name_font_size || 11), 0xFFFFFF, true);



            ntf.defaultTextFormat = nfmt;



            ntf.text = simName;



            var pillPadX:Number = 8;



            var pillPadY:Number = 2.5;



            nameH = Math.round(ntf.textHeight + pillPadY * 2 + 1);



            nameW = Math.round(ntf.textWidth + 4 + pillPadX * 2);



            var nMat:Matrix = new Matrix();



            nMat.createGradientBox(nameW, nameH, Math.PI / 2, 0, 0);



            // 16 Curated Signature Designer Palette Colors (Top, Bottom)



            var palette:Array = [



               [0x569670, 0x3D7252], // 0: Sage Green



               [0x3598A8, 0x227582], // 1: Ocean Teal



               [0x4290B8, 0x2D7092], // 2: Coastal Azure



               [0x4D6BFA, 0x344ECA], // 3: Royal Cobalt



               [0x6966F0, 0x4D4ABF], // 4: Deep Indigo



               [0x896BB8, 0x674D91], // 5: Lavender Violet



               [0xA4559F, 0x7E3A7A], // 6: Berry Magenta



               [0xD6628A, 0xAB4569], // 7: Rose Coral



               [0xD45B4F, 0xA83F34], // 8: Warm Terracotta



               [0xC77934, 0x9B5A1F], // 9: Honey Amber



               [0xB08B32, 0x86671E], // 10: Golden Ochre



               [0x789842, 0x59742B], // 11: Olive Moss



               [0x45A38E, 0x307E6D], // 12: Eucalyptus Mint



               [0x677882, 0x4B5B64], // 13: Slate Steel



               [0x94677A, 0x72495B], // 14: Dusty Mauve



               [0x8B6B54, 0x6B4F3A]  // 15: Warm Espresso



            ];



            var nColorTop:uint = colorTop;



            var nColorBot:uint = colorBot;



            if(nColorTop == 0 || nColorBot == 0)



            {



               var hash:uint = 0;



               for(var chI:int = 0; chI < simId.length; chI++)



               {



                  hash = ((hash << 5) - hash) + simId.charCodeAt(chI);



                  hash &= 0xFFFFFFFF;



               }



               var pIdx:int = int(hash % palette.length);



               nColorTop = uint(palette[pIdx][0]);



               nColorBot = uint(palette[pIdx][1]);



            }



            // Subtle frosted highlight border + volumetric designer gradient



            nameSprite.graphics.lineStyle(1.0, 0xFFFFFF, 0.45, true);



            nameSprite.graphics.beginGradientFill(GradientType.LINEAR, [nColorTop, nColorBot], [1, 1], [0, 255], nMat);



            nameSprite.graphics.drawRoundRect(0, 0, nameW, nameH, nameH, nameH);



            nameSprite.graphics.endFill();



            ntf.x = Math.round((nameW - ntf.width) / 2);



            ntf.y = Math.round((nameH - ntf.textHeight) / 2) - 2;



            nameSprite.addChild(ntf);



         }



         var minBoxW:Number = Math.max(86, hasName ? (nameW + padX * 2) : 70);



         var initialBoxH:Number = 24 + padY * 2 + (hasName ? nameH + 7 : 0) + 6;



         var bg:Shape = new Shape();



         body.addChild(bg);



         var tail:Shape = null;



         if(isThought)



         {



            tail = new Shape();



            body.addChild(tail);



         }



         if(hasName)



         {



            body.addChild(nameSprite);



         }



         body.addChild(tf);



         body.filters = [new DropShadowFilter(5, 90, 0x000000, 0.25, 10, 10, 1, 3)];



         body.scaleX = 0.2;



         body.scaleY = 0.2;



         body.alpha = 0;



         this.balloonLayer.addChild(balloon);



         var offY:Number = Number(sBalloonStyle.offset_y || 32) / 100.0;



         var offX:Number = Number(sBalloonStyle.offset_x || 0) / 100.0;



         var camScale:Boolean = (sBalloonStyle.camera_scale !== false);



         var minSc:Number = Number(sBalloonStyle.min_scale_pct || 35) / 100.0;



         // Call C++ Game Service to bind to head bone



         ExternalInterface.call("CallGameService", "BindDisplayObject", {



            "displayObject": balloon,



            "objectId": simId,



            "attachPoint": "b__Head__",



            "worldOffset": {



               "x": offX,



               "y": offY,



               "z": 0



            },



            "viewOffset": {



               "x": 0,



               "y": 0,



               "z": 0



            },



            "screenOffset": {



               "x": 0,



               "y": 0,



               "z": -0.2



            },



            "isOccludedByWorld": false,



            "isScaledByCamera": camScale,



            "minScale": minSc,



            "maxVisibleScale": 0,



            "lockVisibility": false,



            "lockToScreenEdge": false,



            "lockToScreenEdgeScale": {



               "mTop": 1,



               "mBottom": 1,



               "mBot": 1,



               "mLeft": 1,



               "mRight": 1



            },



            "adjustScreenPositionForMargin": false



         }, false);



         var balloonData:Object = {



            "simId": simId,



            "balloon": balloon,



            "body": body,



            "bg": bg,



            "tail": tail,



            "tf": tf,



            "nameSprite": nameSprite,



            "hasName": hasName,



            "nameW": nameW,



            "nameH": nameH,



            "padX": padX,



            "padY": padY,



            "radius": radius,



            "minBoxW": minBoxW,



            "currentBoxW": minBoxW,



            "currentBoxH": initialBoxH,



            "targetBoxW": minBoxW,



            "targetBoxH": initialBoxH,



            "fullText": text,



            "typedChars": 0,



            "type": balloonType,



            "startTime": getTimer(),



            "duration": durationSec * 1000,



            "state": "opening",



            "stateTime": getTimer(),



            "simName": simName,



            "isPinned": false



         };



         this.activeBalloons[simId] = balloonData;



         this.redrawBalloon(balloonData);



         this.logToServer("createBalloon done: sim=" + simId + ", id=" + this.instanceId);



      }



      private function redrawBalloon(b:Object):void



      {



         var bg:Shape = b.bg as Shape;



         if(!bg) return;



         var boxW:Number = Math.round(b.currentBoxW);



         var boxH:Number = Math.round(b.currentBoxH);



         var left:Number = -Math.round(boxW / 2);



         var top:Number = -boxH;



         var radius:Number = b.radius;



         var isThought:Boolean = (b.type == "thought");



         var themeStr:String = String(sBalloonStyle.theme || "light");



         var bgAlpha:Number = Number(sBalloonStyle.bg_alpha_pct || 98) / 100.0;



         var strokeCol:uint = 0xD4D9E2;



         var fillTop:uint = 0xFFFFFF;



         var fillBot:uint = 0xF4F6F9;



         var textCol:uint = 0x1E1E24;



         if(themeStr == "dark")



         {



            strokeCol = 0x4A5364;



            fillTop = 0x2A303C;



            fillBot = 0x1E232D;



            textCol = 0xF0F3F8;



         }



         else if(themeStr == "warm")



         {



            strokeCol = 0xDECDBB;



            fillTop = 0xFFFAF4;



            fillBot = 0xF7EFE5;



            textCol = 0x2C221A;



         }



         if(b.tf != null)



         {



            (b.tf as TextField).textColor = textCol;



         }



         bg.graphics.clear();



         var bgMat:Matrix = new Matrix();



         bgMat.createGradientBox(boxW, boxH, Math.PI / 2, left, top);



         if(isThought)



         {



            bg.graphics.lineStyle(1.8, strokeCol, bgAlpha, true);



            bg.graphics.beginGradientFill(GradientType.LINEAR, [fillTop, fillBot], [bgAlpha, bgAlpha], [0, 255], bgMat);



            bg.graphics.drawRoundRect(left, top, boxW, boxH, radius, radius);



            bg.graphics.endFill();



            var tail:Shape = b.tail as Shape;



            if(tail != null)



            {



               tail.graphics.clear();



               tail.graphics.lineStyle(1.6, strokeCol, bgAlpha, true);



               tail.graphics.beginFill(fillTop, bgAlpha);



               tail.graphics.drawCircle(-6, top + boxH + 8, 4.6);



               tail.graphics.drawCircle(-3, top + boxH + 17, 3.2);



               tail.graphics.drawCircle(0, top + boxH + 24, 1.9);



               tail.graphics.endFill();



            }



         }



         else



         {



            bg.graphics.lineStyle(1.8, strokeCol, bgAlpha, true);



            bg.graphics.beginGradientFill(GradientType.LINEAR, [fillTop, fillBot], [bgAlpha, bgAlpha], [0, 255], bgMat);



            bg.graphics.drawRoundRect(left, top, boxW, boxH, radius, radius);



            bg.graphics.endFill();



            // Pointer triangle at x = 0



            bg.graphics.lineStyle(1.8, strokeCol, bgAlpha, true);



            bg.graphics.beginFill(fillBot, bgAlpha);



            bg.graphics.moveTo(-8, top + boxH);



            bg.graphics.lineTo(0, top + boxH + 10);



            bg.graphics.lineTo(8, top + boxH);



            bg.graphics.endFill();



            // Erase dividing border line across base of pointer



            bg.graphics.lineStyle(2.4, fillBot, bgAlpha);



            bg.graphics.moveTo(-7, top + boxH);



            bg.graphics.lineTo(7, top + boxH);



         }



         var curY:Number = top + b.padY;



         if(b.hasName && b.nameSprite != null)



         {



            b.nameSprite.x = left + b.padX;



            b.nameSprite.y = curY;



            curY += b.nameH + 7;



         }



         if(b.tf != null)



         {



            b.tf.x = left + b.padX;



            b.tf.y = curY;



         }



      }



      private function onEnterFrame(e:Event):void



      {



         var now:Number = getTimer();



         var toRemove:Array = [];



         for(var key:* in this.activeBalloons)



         {



            var b:Object = this.activeBalloons[key];



            var elapsed:Number = now - b.startTime;



            var body:Sprite = b.body as Sprite;



            var scaleMult:Number = Number(sBalloonStyle.scale_pct || 100) / 100.0;



            // Typewriter effect & dynamic real-time auto-expansion



            if(b.tf != null && b.fullText != null)



            {



               var typeElapsed:Number = now - b.startTime - 80;



               if(typeElapsed > 0)



               {



                  var typeSpeedVal:Number = Number(sBalloonStyle.type_speed != null ? sBalloonStyle.type_speed : 35);



                  var targetCount:int = (typeSpeedVal <= 0) ? b.fullText.length : Math.min(b.fullText.length, Math.floor(typeElapsed * (typeSpeedVal / 1000.0)));



                  if(targetCount != b.typedChars)



                  {



                     b.typedChars = targetCount;



                     var currentText:String = b.fullText.substr(0, targetCount);



                     (b.tf as TextField).text = currentText;



                     var curTextW:Number = Math.ceil((b.tf as TextField).textWidth) + 8;



                     var curTextH:Number = Math.ceil((b.tf as TextField).textHeight);



                     if(curTextH < 22)



                     {



                        curTextH = 22;



                     }



                     var contentW:Number = Math.max(curTextW, b.hasName ? b.nameW : 0);



                     b.targetBoxW = Math.max(b.minBoxW, contentW + b.padX * 2);



                     b.targetBoxH = curTextH + b.padY * 2 + (b.hasName ? b.nameH + 7 : 0) + 6;



                  }



               }



            }



            // Smoothly interpolate width and height towards target size



            var dw:Number = b.targetBoxW - b.currentBoxW;



            var dh:Number = b.targetBoxH - b.currentBoxH;



            if(Math.abs(dw) > 0.4 || Math.abs(dh) > 0.4)



            {



               b.currentBoxW += dw * 0.45;



               b.currentBoxH += dh * 0.45;



               this.redrawBalloon(b);



            }



            else if(b.currentBoxW != b.targetBoxW || b.currentBoxH != b.targetBoxH)



            {



               b.currentBoxW = b.targetBoxW;



               b.currentBoxH = b.targetBoxH;



               this.redrawBalloon(b);



            }



            // The Sims 4 C++ camera engine updates bSpr.scaleX and bSpr.scaleY every frame.



            // Overriding bSpr.scale directly in ActionScript creates a frame-by-frame fight



            // between C++ and Flash, resulting in violent jitter/shaking when zoomed in.



            // Instead, we leave bSpr.scale untouched, and counter-scale the inner body



            // so on-screen size smoothly caps at 1.0 without any jitter.



            var bSpr:Sprite = b.balloon as Sprite;



            var maxBodyScale:Number = 1.0;



            if(bSpr != null && bSpr.scaleX > 1.0)



            {



               maxBodyScale = 1.0 / bSpr.scaleX;



            }



            if(b.state == "opening")



            {



               var openElapsed:Number = now - b.stateTime;



               var t:Number = Math.min(1.0, openElapsed / 220.0);



               var c1:Number = 1.70158;



               var c3:Number = c1 + 1;



               var s:Number = 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);



               body.scaleX = Math.max(0, s) * maxBodyScale * scaleMult;



               body.scaleY = Math.max(0, s) * maxBodyScale * scaleMult;



               body.alpha = Math.min(1.0, t * 1.5);



               if(t >= 1.0)



               {



                  body.scaleX = maxBodyScale * scaleMult;



                  body.scaleY = maxBodyScale * scaleMult;



                  body.alpha = 1.0;



                  b.state = "holding";



                  b.stateTime = now;



               }



            }



            else if(b.state == "holding")



            {



               var holdElapsed:Number = now - b.stateTime;



               var breath:Number = 1.0 + 0.008 * Math.sin(holdElapsed * 0.003);



               body.alpha = 1.0;



               body.scaleX = breath * maxBodyScale * scaleMult;



               body.scaleY = breath * maxBodyScale * scaleMult;



               if(elapsed >= b.duration && !b.isPinned)



               {



                  b.state = "closing";



                  b.stateTime = now;



               }



            }



            else if(b.state == "closing")



            {



               var closeElapsed:Number = now - b.stateTime;



               var ct:Number = Math.min(1.0, closeElapsed / 250.0);



               body.scaleX = (1.0 - ct * 0.3) * maxBodyScale * scaleMult;



               body.scaleY = (1.0 - ct * 0.3) * maxBodyScale * scaleMult;



               body.alpha = 1.0 - ct;



               if(ct >= 1.0)



               {



                  toRemove.push(b);



               }



            }



         }



         for(var i:int = 0; i < toRemove.length; i++)



         {



            this.removeBalloon(toRemove[i]);



         }



      }



      private function removeBalloon(b:Object):void



      {



         try



         {



            ExternalInterface.call("CallGameService", "UnbindDisplayObject", {



               "displayObject": b.balloon



            }, false);



         }



         catch(err:Error) {}



         try



         {



            if(b.balloon && b.balloon.parent)



            {



               b.balloon.parent.removeChild(b.balloon);



            }



         }



         catch(e2:Error) {}



         if(b.simId && this.activeBalloons[b.simId] == b)



         {



            delete this.activeBalloons[b.simId];



         }



      }



   }



}



// =========================================================================



// SYNAPSE SETTINGS UI — PIXEL-PERFECT THE SIMS 4 "НАСТРОЙКИ ИГРЫ" REPLICA



// ZERO lineStyle ON CURVES (100% FILLED GEOMETRY FOR FLAWLESS CORNERS)



// NATIVE $TextFont WITHOUT SMALL-CAPS DISTORTION



// =========================================================================



import flash.display.GradientType;



import flash.display.Shape;



import flash.display.Sprite;



import flash.events.Event;



import flash.events.FocusEvent;



import flash.events.KeyboardEvent;



import flash.events.MouseEvent;



import flash.external.ExternalInterface;



import flash.filters.DropShadowFilter;



import flash.geom.Matrix;



   import flash.geom.Rectangle;



import flash.text.TextField;



import flash.text.TextFieldAutoSize;



import flash.text.TextFormat;



import flash.utils.ByteArray;



import flash.utils.getDefinitionByName;



import flash.utils.getTimer;



class SettingsUI extends Sprite



{



    // Точные пропорции окна "НАСТРОЙКИ ИГРЫ" The Sims 4



    public static const WIN_W:Number = 880;



    public static const WIN_H:Number = 606;



    public static const HEADER_H:Number = 62;



    public static const FOOTER_H:Number = 64;



    public static const SIDEBAR_W:Number = 172;



    public static const WORKSPACE_X:Number = 184;



    public static const WORKSPACE_W:Number = 682;



    // Точная цветовая палитра из попиксельного сканирования оригинального окна The Sims 4



    public static const COL_ROYAL_BLUE:uint  = 0x0D4CAC; // Заголовки, значения списков, кнопки



    public static const COL_HOVER_GREEN:uint = 0x35B212; // Фирменный зелёный цвет текста/стрелки при наведении в Sims 4



    public static const COL_LABEL_BLUE:uint  = 0x1E7AE0; // Голубые подписи настроек ("Тип экрана:")



    public static const COL_SEC_HEADER:uint  = 0xA3B1BF; // Плашки секций ("ЭКРАН", "ГРАФИКА")



    public static const COL_ICE_BANNER:uint  = 0xEAF1F8; // Выделенная полоса ("Качество графики")



    public static const COL_GREEN_TOP:uint   = 0x8FE455; // Верх активной вкладки (#8FE455)



    public static const COL_GREEN_BOT:uint   = 0x3BBE15; // Низ активной вкладки (#3BBE15)



    public static const COL_TAB_TOP:uint     = 0xFEFEFE; // Верх обычной вкладки (#FEFEFE)



    public static const COL_TAB_BOT:uint     = 0xECECEC; // Низ обычной вкладки (#ECECEC)



    public static const COL_FOOTER_TOP:uint  = 0xAEB7CA; // Верх футера (#AEB7CA)



    public static const COL_FOOTER_BOT:uint  = 0xC8CED9; // Низ футера (#C8CED9)



    public static const COL_BOX_BORDER:uint  = 0xDCE3EC;



    public static const COL_LABEL_DARK:uint  = 0x1A344B; // Тонкая рамка секций



    private var mDimmer:Sprite;



    private var mWindow:Sprite;



    private var mWorkspace:Sprite;



    private var mDefaultContainer:Sprite;



    private var mLoreContainer:Sprite;



    // --- LORE SECTION STATE ---



    public var mCurrentSimId:String = "0";



    public var mCurrentSimName:String = "";



    public var mCurrentLoreText:String = "";



    public var mSelectedSimLabel:TextField;



    public var mLoreStatusLabel:TextField;



    public var mLoreInput:TextField;



    public var mLoreRaceInput:TextField;



    public var mLoreCounter:TextField;



    public var mLoreSavedBadge:TextField;



    public var mCurrentRaceText:String = "";



    public var mSelectedMemorySimId:String = "";



    public var mSelectedMemorySimName:String = "";



    public var mMemorySimLabel:TextField;



    public var mMemoryTextInput:TextField;



    public var mMemoryDaysInput:TextField;



    public var mMemoryCreatedBadge:TextField;



    // --- CONTEXT SECTION STATE ---



    public var mContextContainer:Sprite;



    public var mCurrentContextMode:String = "thought";



    public var mContextFlagsState:Object = {};



    public var mContextScrollView:MaxisScrollView;



    public var mAccordionSections:Array = [];



    public var mCheckboxesByKey:Object = {};



    public var mExpandedSections:Object = {};



    public var mModeBtns:Array = [];



    // --- AUTONOMY SECTION STATE ---



    public var mAutonomyContainer:Sprite;



    public var mAutonomyEnabled:Boolean = true;



    public var mAutonomyInterval:int = 240;



    public var mAutonomyCheckbox:SimsCheckbox;



    public var mAutonomyStatusTf:TextField;



    public var mAutonomyCustomInput:TextField;



    public var mAutonomyPresetBtns:Array = [];



    public var mAutonomySavedBadge:TextField;



    public var mContextHintTf:TextField;



    public var mContextListContainer:Sprite;



    public var mContextPage:int = 0;



    public var mContextPageTf:TextField;



    public var mContextPrevBtn:Sprite;



    public var mContextNextBtn:Sprite;



    // --- GENEALOGY SECTION STATE ---



    public var mGenealogyContainer:Sprite;



    public var mGenealogyFlagsState:Object = {};



    public var mGenealogyDepth:int = 10;



    public var mGenealogyScrollView:MaxisScrollView;



    public var mGenealogyAccordionSections:Array = [];



    public var mGenealogyCheckboxesByKey:Object = {};



    public var mGenealogyExpandedSections:Object = {};



    public var mGenealogyDepthBtns:Array = [];



    // --- MEMORY SECTION STATE ---



    public var mMemoryContainer:Sprite;



    public var mEventMemoryEnabled:Boolean = true;



    public var mDialogueMemoryHours:int = 24;



    public var mSummarizePersonal:Boolean = true;



    public var mSummarizeGroup:Boolean = true;



    public var mMemoryScrollView:MaxisScrollView;



    public var mMemoryAccordionSections:Array = [];



    public var mMemoryCheckboxesByKey:Object = {};



    public var mMemoryExpandedSections:Object = {};



    public var mMemoryHoursBtns:Array = [];



    // --- MODS INTEGRATION SECTION STATE ---



    public var mModsContainer:Sprite;



    public var mWwSexMode:String = "bed_picker";



    public var mModsScrollView:MaxisScrollView;



    public var mModsAccordionSections:Array = [];



    public var mModsOptionRowsByKey:Object = {};



    public var mModsOptionIndicatorsByKey:Object = {};



    public var mModsExpandedSections:Object = {};



    // --- DISPLAY & NOTIFICATION SECTION STATE ---



    public var mDisplayContainer:Sprite;



    public var mDisplayFlagsState:Object = {



        "thought_balloon": true,



        "thought_notification": true,



        "direct_balloon": true,



        "direct_notification": true,



        "director_balloon": true,



        "director_notification": false



    };



    public var mDisplayScrollView:MaxisScrollView;



    public var mDisplayAccordionSections:Array = [];



    public var mDisplayCheckboxesByKey:Object = {};



    public var mDisplayExpandedSections:Object = {};



    // --- AUTONOMOUS DIRECTOR SECTION STATE ---



    public var mDirectorContainer:Sprite;
    public var mSimplifiedContainer:Sprite;
    public var mSimplifiedMasterCheckbox:SimsCheckbox;
    public var mSimplifiedEnabled:Boolean = false;
    public var mSimplifiedSilenceSec:int = 180;
    public var mSimplifiedChancePct:int = 40;
    public var mSimplifiedBalloon:Boolean = true;
    public var mSimplifiedNotif:Boolean = false;
    public var mSimplifiedInSilence:TextField;
    public var mSimplifiedInChance:TextField;
    public var mSimplifiedCbBalloon:SimsCheckbox;
    public var mSimplifiedCbNotif:SimsCheckbox;



    public var mDirectorEnabled:Boolean = false;



    public var mDirectorDisabledTriggers:Object = {};



    public var mDirectorCurrentState:String = "HOME";



    public var mDirectorMasterCheckbox:SimsCheckbox;



    public var mDirectorStateButtons:Array = [];



    public var mDirectorScrollView:MaxisScrollView;



    public var mDirectorCheckboxesByTrigger:Object = {};



    public var mDirectorStateButtonsContainer:Sprite;



    public var mDirectorCurrentStateTitleTf:TextField;



    public var mDirectorSilenceSec:int = 240;



    public var mDirectorPairSec:int = 450;



    public var mDirectorGraceSec:int = 60;



    public var mDirectorOverrides:Object = {};



    public var mMultisimRules:Object = {};

    public var mDefaultMultisimRules:Object = {

        "group_chat": "- ЭТО ГРУППОВОЙ ДИАЛОГ! Все перечисленные персонажи общаются вместе в одной компании. Если реплика обращена ко всем («привет девочки», «как вы?», «народ», вопрос к компании) или касается присутствующих — другие участники разговора ОБЯЗАТЕЛЬНО подхватывают беседу через разделитель «///» со своими ответами по очереди! (Формат: Ответ первого собеседника [FR=...] [ROM=...] /// Имя: Ответ второго собеседника [FR=...] [ROM=...]). Если фраза адресована строго одному по имени («Мимси, поцелуй меня») — отвечает только адресат.",

        "bystander": "- Персонаж рядом встревает ИСКЛЮЧИТЕЛЬНО РЕДКО (через «///» или [JOIN=...]) — только если назвали его имя («Эй, Данте!»), задели его лично/семью или прямо обратились к нему. В обычных разговорах между собеседниками персонаж рядом молча занимается своими делами и НЕ встревает!",

        "sex_group": "- ЭТО СОВМЕСТНЫЙ ИНТИМНЫЙ АКТ (ГРУППОВОЙ СЕКС / СЕКС ВТРОЁМ И Т.Д.)! Все перечисленные персонажи находятся в процессе близости вместе с вами. Если реплика обращена ко всем участникам («как вам?», «девочки...», стон или вопрос к участникам) или касается происходящего — другие участники интима ОБЯЗАТЕЛЬНО подхватывают разговор через разделитель «///» со своими реакциями, стонами, репликами и тегами! (Формат: Ответ первого партнера [FR=...] [ROM=...] /// Имя: Ответ второго партнера [FR=...] [ROM=...]). Опционально разрешены [DO=stop_sex] (прервать секс) и [SUM=...|Day=N] (важное воспоминание).",

        "sex_bystander": "- Персонаж находится рядом в комнате как свидетель или наблюдатель. Свидетель встревает ИСКЛЮЧИТЕЛЬНО РЕДКО (через «///») — только если заговорили прямо с ним, назвали его имя или задели его лично. В обычных интимных репликах участников между собой свидетель МОЛЧИТ и не встревает! Если свидетель вступает в разговор и согласен присоединиться, он может использовать [DO=join_sex], а если возмущен — потребовать прекратить [DO=stop_sex]."

    };

    public var mActiveMultisimRuleKey:String = "group_chat";

    public var mMultisimRuleInput:TextField = null;



    public var mDirectorModalOverlay:Sprite = null;



    public var mStudioPanel:BalloonStudioUI = null;



    // --- WORLDS / CITIES SECTION STATE ---



    public var mWorldsContainer:Sprite;



    public var mWorldsScrollView:MaxisScrollView;



    public var mWorldButtonsContainer:Sprite;



    public var mWorldButtons:Array = [];



    public var mCurrentWorldKey:String = "Виллоу Крик";



    public var mActiveLotWorldKey:String = "Виллоу Крик";



    public var mCustomWorldData:Object = {};



    public var mWorldTitleLabel:TextField;



    public var mWorldStatusLabel:TextField;



    public var mWorldCustomNameInput:TextField;



    public var mWorldDescInput:TextField;



    public var mWorldCounter:TextField;



    public var mWorldSavedBadge:TextField;



// (Worlds list and default descriptions defined via methods)



    // --- EXPERIMENTAL SECTION STATE ---



    public var mExperimentalContainer:Sprite;



    public var mExperimentalFlagsState:Object = {



        "dynamic_interaction_ui_fallback": false,



        "home_business_context": false,



        "direct_dialogue_pause": true,



        "direct_dialogue_multisim_join": true,

        "direct_dialogue_approach_first": true,



        "alien_male_pregnancy": true,



        "classic_insane_trait": false,



        "overheard_conversations": false,



        "third_party_dossier": false,



        "trapped_sim_detection": false,



        "last_thought_context": false



    };



    public var mExperimentalScrollView:MaxisScrollView;



    public var mExperimentalAccordionSections:Array = [];



    public var mExperimentalCheckboxesByKey:Object = {};



    public var mExperimentalExpandedSections:Object = {};



    private var mSecTitle1:TextField;



    private var mSecTitle2:TextField;



    private var mCloseBtn:Sprite;



    private var mCloseBg:Shape;



    private var mCloseIcon:Shape;



    private var mTabs:Array = [];



    private var mDragging:Boolean = false;



    private var mDragX:Number = 0;



    private var mDragY:Number = 0;



    private var mBaseX:Number = 0;



    private var mBaseY:Number = 0;



    // Покадровые кривые анимации появления и закрытия окна (сняты с 30fps записи The Sims 4)



    private var mAnimMode:int = 0; // 0 = покой, 1 = открытие, 2 = закрытие



    private var mAnimStart:int = 0;



    private var mOpenSy:Array    = [0.531, 0.767, 0.916, 1.013, 1.052, 1.058, 1.045, 1.023, 1.006, 1.000];



    private var mOpenAlpha:Array = [0.82,  0.94,  1.00,  1.00,  1.00,  1.00,  1.00,  1.00,  1.00,  1.00];



    private var mCloseScale:Array = [1.000, 1.028, 1.071, 1.075, 0.972, 0.722, 0.450];



    private var mCloseAlpha:Array = [1.00,  1.00,  1.00,  1.00,  0.92,  0.60,  0.00];



    private var mTabTitles:Array = [



        "Личная история",



        "Настройки контекста",



        "Автономия мыслей",



        "Родство и связи",



        "Память и общение",



        "Интеграция с модами",



        "Уведомления и баблы",



        "Режиссёр общения",







        "Упрощённое общение",







        "Описания городов",



        "Экспериментальное"



    ];



    private var mSec1Names:Array = [



        "ЭКРАН И ОБЛАЧКА",



        "ПОДКЛЮЧЕНИЕ И КЛЮЧИ",



        "СВОБОДА ВОЛИ СИМОВ",



        "СЮЖЕТНЫЙ РЕЖИССЁР",



        "ВИЗУАЛИЗАЦИЯ ОБЛАЧКОВ",



        "ДОЛГОВРЕМЕННАЯ ПАМЯТЬ",



        "СОЦИАЛЬНАЯ СЕТЬ И ПК",



        "РОМАНТИКА И РЕВНОСТЬ",



        "ГЕНЕРАЦИЯ СОБЫТИЙ",



        "СИСТЕМНЫЕ ОПЦИИ"



    ];



    private var mSec2Names:Array = [



        "ИИ И СИМУЛЯЦИЯ",



        "ВЫБОР МОДЕЛИ И ТОКЕНОВ",



        "ИНТЕНСИВНОСТЬ АВТОНОМИИ",



        "ДРАМАТУРГИЯ И СЦЕНАРИИ",



        "ШРИФТ И ВРЕМЯ ПОКАЗА",



        "КОНТЕКСТ ПЕРСОНАЖЕЙ",



        "ЧАТЫ И УВЕДОМЛЕНИЯ",



        "ПРОВЕРКА ИЗМЕН (8 МИН)",



        "ЧАСТОТА И ПРОМПТЫ",



        "ОТЛАДКА И ЛОГИРОВАНИЕ"



    ];



    public function SettingsUI()



    {



        super();



        this.mouseEnabled = false;



        this.mouseChildren = false;



        this.visible = false;



        this.registerCommands();



        if (stage)



        {



            this.init(null);



        }



        else



        {



            addEventListener(Event.ADDED_TO_STAGE, this.init);



        }



    }



    private function init(e:Event):void



    {



        removeEventListener(Event.ADDED_TO_STAGE, this.init);



        try



        {



            this.buildUI();



        }



        catch(errBuild:Error)



        {



            try {



                ExternalInterface.call("CallGameService", "PostServerCommand", {



                    "command": "synapse.ui_log",



                    "commandArgs": ["SettingsUI.buildUI ERROR: " + errBuild.message]



                }, false);



            } catch(eLog:Error) {}



        }



        this.registerCommands();



        this.centerWindow();



        if (stage)



        {



            stage.addEventListener(Event.RESIZE, this.onStageResize);



            stage.addEventListener(MouseEvent.MOUSE_UP, this.onStageMouseUp);



            stage.addEventListener(MouseEvent.MOUSE_MOVE, this.onDragMove);



            stage.addEventListener(KeyboardEvent.KEY_DOWN, this.onStageKeyDown, true);



            // focus listener removed



            // focus listener removed



            // focus listener removed



        }



    }



    private function setTextInputCapture(on:Boolean):void



    {



        try



        {



            var cm:Object = getDefinitionByName("olympus.io.CommunicationManager");



            // removed to prevent C++ crash



        }



        catch (errTf:Error) {}



    }



    private function grabStageFocus():void



    {



        try



        {



            if (stage && stage.focus is TextField && (stage.focus as TextField).type == "input")



            {



                // text input capture



                return;



            }



            if (stage && this.mWindow && this.visible && this.mAnimMode != 2)



            {



                this.mWindow.focusRect = false;



                this.mWindow.tabEnabled = false;



                stage.focus = this.mWindow;



            }



        }



        catch (errFoc:Error) {}



    }



    private function dropStageFocus():void



    {



        try



        {



            if (stage && stage.focus != null)



            {



                stage.focus = null;



            }



        }



        catch (errDrop:Error) {}



    }



    private function onFocusKeep(ev:FocusEvent):void



    {



        if (this.visible && this.mAnimMode != 2)



        {



            // text input capture



        }



    }



    private function onStageKeyDown(ev:KeyboardEvent):void



    {



        if (this.visible && this.mAnimMode != 2 && ev.keyCode == 27)



        {



            ev.stopImmediatePropagation();



            if (this.mDirectorModalOverlay != null)



            {



                this.closeDirectorModal();



            }



            else if (this.mOpenDropdown != null)



            {



                this.closeActivePopup();



            }



            else



            {



                this.setModal(false);



            }



        }



    }



    private function onStageResize(ev:Event):void



    {



        this.drawDimmer();



        this.centerWindow();



    }



    private function onStageMouseUp(ev:MouseEvent):void



    {



        this.mDragging = false;



    }



    // =====================================================================



    // СВЯЗЬ PYTHON <-> FLASH



    // =====================================================================



    private function registerCommands():void



    {



        try



        {



            var dbg:Object = getDefinitionByName("olympus.io.DebugCommands");



            dbg.Register("ui.synapse_settings", this.onSettingsCommand, "Synapse Settings UI", "");



            dbg.Register("synapse.open_settings", this.onSettingsCommand, "Synapse Settings UI", "");



            dbg.Register("synapse.settings", this.onSettingsCommand, "Synapse Settings UI", "");



        }



        catch (err:Error) {}



    }



    public function onSettingsCommand(args:Array, params:Object = null, ctx:String = ""):void



    {



        this.handleSettingsCommand(args);



    }



    public function handleSettingsCommand(args:Array):void



    {



        if (args && args.length > 0)



        {



            var cmd:String = String(args[0]).toLowerCase();



                        if (cmd == "close")

            {

                this.setModal(false);

                return;

            }

            if (cmd == "balloon_style")

            {

                if (args.length > 1 && Boot.sActiveInstance != null)

                {

                    Boot.sActiveInstance.applyBalloonStyle(String(args[1]));

                }

                return;

            }

            if (cmd == "studio_start")

            {

                var stSimId:String = (args.length > 1) ? String(args[1]) : "0";

                var stSimName:String = (args.length > 2) ? this.decodeSafeStr(String(args[2])) : "Сим";

                this.onStudioStartFromPython(stSimId, stSimName);

                return;

            }

            if (cmd == "studio_stop")

            {

                this.closeBalloonStudio(false);

                return;

            }



            if (cmd == "saved")



            {



                this.onLoreSavedCommand(args);



                return;



            }



            if (cmd == "cleared")



            {



                this.onLoreClearedCommand(args);



                return;



            }



            if (cmd == "autonomy")



            {



                this.setModal(true);



                if (args.length >= 3)



                {



                    var aId:String = String(args[1]);



                    var aName:String = String(args[2]);



                    var aLore:String = (args.length > 3) ? String(args[3]) : "00";



                    this.onLoreDataCommand([aId, aName, aLore]);



                }



                if (args.length >= 5)



                {



                    this.parseContextState(String(args[4]));



                    this.rebuildContextItems();



                }



                if (args.length >= 6)



                {



                    this.mAutonomyEnabled = (String(args[5]) == "1" || String(args[5]).toLowerCase() == "true");



                }



                if (args.length >= 7)



                {



                    var pIntA:int = parseInt(String(args[6]));



                    if (pIntA > 0) this.mAutonomyInterval = pIntA;



                }



                if (args.length >= 8)



                {



                    this.parseGenealogyState(String(args[7]));



                }



                if (args.length >= 9)



                {



                    this.parseMemoryState(String(args[8]));



                }



                if (args.length >= 10)



                {



                    this.parseModsState(String(args[9]));



                }



                if (args.length >= 11)



                {



                    this.parseDisplayState(String(args[10]));



                }



                if (args.length >= 12)



                {



                    this.parseWorldLoreState(String(args[11]));



                }



                if (args.length >= 13)



                {



                    this.parseExperimentalState(String(args[12]));



                }



                if (args.length >= 14)



                {



                    this.parseDirectorState(String(args[13]));



                }



                this.selectTab(2);



                return;



            }



            if (cmd == "lore_sim")



            {



                var lsId:String = String(args[1]);



                var lsName:String = String(args[2]);



                var lsLore:String = (args.length > 3) ? String(args[3]) : "00";



                var lsRace:String = (args.length > 4) ? String(args[4]) : "00";



                this.onLoreDataCommand([lsId, lsName, lsLore, lsRace]);



                return;



            }



            if (cmd == "memory_sim")



            {



                var memSimId:String = String(args[1]);



                var memSimName:String = this.decodeSafeStr(String(args[2]));



                this.mSelectedMemorySimId = memSimId;



                this.mSelectedMemorySimName = memSimName;



                if (this.mMemorySimLabel != null)



                {



                    this.mMemorySimLabel.text = "Персонаж: " + memSimName + " [ID: " + memSimId + "]";



                }



                return;



            }



            if (cmd == "memory_created")



            {



                if (this.mMemoryCreatedBadge != null)



                {



                    this.mMemoryCreatedBadge.text = "Воспоминание сохранено!";



                    this.mMemoryCreatedBadge.visible = true;



                }



                if (this.mMemoryTextInput != null)



                {



                    this.mMemoryTextInput.text = "";



                }



                return;



            }



            if (cmd == "lore")



            {



                this.setModal(true);



                this.selectTab(0);



                if (args.length >= 3)



                {



                    var sId:String = String(args[1]);



                    var sName:String = String(args[2]);



                    var sLore:String = (args.length > 3) ? String(args[3]) : "00";



                    var sRace:String = (args.length > 14) ? String(args[14]) : ((args.length == 5) ? String(args[4]) : "00");



                    this.onLoreDataCommand([sId, sName, sLore, sRace]);



                }



                if (args.length >= 5)



                {



                    this.parseContextState(String(args[4]));



                    this.rebuildContextItems();



                }



                if (args.length >= 6)



                {



                    this.mAutonomyEnabled = (String(args[5]) == "1" || String(args[5]).toLowerCase() == "true");



                }



                if (args.length >= 7)



                {



                    var pIntL:int = parseInt(String(args[6]));



                    if (pIntL > 0) this.mAutonomyInterval = pIntL;



                }



                if (args.length >= 8)



                {



                    this.parseGenealogyState(String(args[7]));



                }



                if (args.length >= 9)



                {



                    this.parseMemoryState(String(args[8]));



                }



                if (args.length >= 10)



                {



                    this.parseModsState(String(args[9]));



                }



                if (args.length >= 11)



                {



                    this.parseDisplayState(String(args[10]));



                }



                if (args.length >= 12)



                {



                    this.parseWorldLoreState(String(args[11]));



                }



                if (args.length >= 13)



                {



                    this.parseExperimentalState(String(args[12]));



                }



                if (args.length >= 14)



                {



                    this.parseDirectorState(String(args[13]));



                }



                return;



            }



            if (cmd == "context")



            {



                this.setModal(true);



                if (args.length >= 3)



                {



                    var cId:String = String(args[1]);



                    var cName:String = String(args[2]);



                    var cLore:String = (args.length > 3) ? String(args[3]) : "00";



                    this.onLoreDataCommand([cId, cName, cLore]);



                }



                if (args.length >= 5)



                {



                    this.parseContextState(String(args[4]));



                    this.rebuildContextItems();



                }



                if (args.length >= 6)



                {



                    this.mAutonomyEnabled = (String(args[5]) == "1" || String(args[5]).toLowerCase() == "true");



                }



                if (args.length >= 7)



                {



                    var pIntC:int = parseInt(String(args[6]));



                    if (pIntC > 0) this.mAutonomyInterval = pIntC;



                }



                if (args.length >= 8)



                {



                    this.parseGenealogyState(String(args[7]));



                }



                if (args.length >= 9)



                {



                    this.parseMemoryState(String(args[8]));



                }



                if (args.length >= 10)



                {



                    this.parseModsState(String(args[9]));



                }



                if (args.length >= 11)



                {



                    this.parseDisplayState(String(args[10]));



                }



                if (args.length >= 12)



                {



                    this.parseWorldLoreState(String(args[11]));



                }



                if (args.length >= 13)



                {



                    this.parseExperimentalState(String(args[12]));



                }



                if (args.length >= 14)



                {



                    this.parseDirectorState(String(args[13]));



                }



                this.selectTab(1);



                return;



            }



            if (cmd == "genealogy")



            {



                this.setModal(true);



                if (args.length >= 3)



                {



                    var gId:String = String(args[1]);



                    var gName:String = String(args[2]);



                    var gLore:String = (args.length > 3) ? String(args[3]) : "00";



                    this.onLoreDataCommand([gId, gName, gLore]);



                }



                if (args.length >= 5)



                {



                    this.parseContextState(String(args[4]));



                    this.rebuildContextItems();



                }



                if (args.length >= 6)



                {



                    this.mAutonomyEnabled = (String(args[5]) == "1" || String(args[5]).toLowerCase() == "true");



                }



                if (args.length >= 7)



                {



                    var pIntG:int = parseInt(String(args[6]));



                    if (pIntG > 0) this.mAutonomyInterval = pIntG;



                }



                if (args.length >= 8)



                {



                    this.parseGenealogyState(String(args[7]));



                }



                if (args.length >= 9)



                {



                    this.parseMemoryState(String(args[8]));



                }



                if (args.length >= 10)



                {



                    this.parseModsState(String(args[9]));



                }



                if (args.length >= 11)



                {



                    this.parseDisplayState(String(args[10]));



                }



                if (args.length >= 12)



                {



                    this.parseWorldLoreState(String(args[11]));



                }



                if (args.length >= 13)



                {



                    this.parseExperimentalState(String(args[12]));



                }



                if (args.length >= 14)



                {



                    this.parseDirectorState(String(args[13]));



                }



                this.selectTab(3);



                return;



            }



            if (cmd == "memory")



            {



                this.setModal(true);



                if (args.length >= 3)



                {



                    var memId:String = String(args[1]);



                    var memName:String = String(args[2]);



                    var memLore:String = (args.length > 3) ? String(args[3]) : "00";



                    this.onLoreDataCommand([memId, memName, memLore]);



                }



                if (args.length >= 5)



                {



                    this.parseContextState(String(args[4]));



                    this.rebuildContextItems();



                }



                if (args.length >= 6)



                {



                    this.mAutonomyEnabled = (String(args[5]) == "1" || String(args[5]).toLowerCase() == "true");



                }



                if (args.length >= 7)



                {



                    var pIntM:int = parseInt(String(args[6]));



                    if (pIntM > 0) this.mAutonomyInterval = pIntM;



                }



                if (args.length >= 8)



                {



                    this.parseGenealogyState(String(args[7]));



                }



                if (args.length >= 9)



                {



                    this.parseMemoryState(String(args[8]));



                }



                if (args.length >= 10)



                {



                    this.parseModsState(String(args[9]));



                }



                if (args.length >= 11)



                {



                    this.parseDisplayState(String(args[10]));



                }



                if (args.length >= 12)



                {



                    this.parseWorldLoreState(String(args[11]));



                }



                if (args.length >= 13)



                {



                    this.parseExperimentalState(String(args[12]));



                }



                if (args.length >= 14)



                {



                    this.parseDirectorState(String(args[13]));



                }



                this.selectTab(4);



                return;



            }



            if (cmd == "mods")



            {



                this.setModal(true);



                if (args.length >= 3)



                {



                    var mdId:String = String(args[1]);



                    var mdName:String = String(args[2]);



                    var mdLore:String = (args.length > 3) ? String(args[3]) : "00";



                    this.onLoreDataCommand([mdId, mdName, mdLore]);



                }



                if (args.length >= 5)



                {



                    this.parseContextState(String(args[4]));



                    this.rebuildContextItems();



                }



                if (args.length >= 6)



                {



                    this.mAutonomyEnabled = (String(args[5]) == "1" || String(args[5]).toLowerCase() == "true");



                }



                if (args.length >= 7)



                {



                    var pIntMd:int = parseInt(String(args[6]));



                    if (pIntMd > 0) this.mAutonomyInterval = pIntMd;



                }



                if (args.length >= 8)



                {



                    this.parseGenealogyState(String(args[7]));



                }



                if (args.length >= 9)



                {



                    this.parseMemoryState(String(args[8]));



                }



                if (args.length >= 10)



                {



                    this.parseModsState(String(args[9]));



                }



                if (args.length >= 11)



                {



                    this.parseDisplayState(String(args[10]));



                }



                if (args.length >= 12)



                {



                    this.parseWorldLoreState(String(args[11]));



                }



                if (args.length >= 13)



                {



                    this.parseExperimentalState(String(args[12]));



                }



                if (args.length >= 14)



                {



                    this.parseDirectorState(String(args[13]));



                }



                this.selectTab(5);



                return;



            }



            if (cmd == "display")



            {



                this.setModal(true);



                if (args.length >= 3)



                {



                    var dpId:String = String(args[1]);



                    var dpName:String = String(args[2]);



                    var dpLore:String = (args.length > 3) ? String(args[3]) : "00";



                    this.onLoreDataCommand([dpId, dpName, dpLore]);



                }



                if (args.length >= 5)



                {



                    this.parseContextState(String(args[4]));



                    this.rebuildContextItems();



                }



                if (args.length >= 6)



                {



                    this.mAutonomyEnabled = (String(args[5]) == "1" || String(args[5]).toLowerCase() == "true");



                }



                if (args.length >= 7)



                {



                    var pIntDp:int = parseInt(String(args[6]));



                    if (pIntDp > 0) this.mAutonomyInterval = pIntDp;



                }



                if (args.length >= 8)



                {



                    this.parseGenealogyState(String(args[7]));



                }



                if (args.length >= 9)



                {



                    this.parseMemoryState(String(args[8]));



                }



                if (args.length >= 10)



                {



                    this.parseModsState(String(args[9]));



                }



                if (args.length >= 11)



                {



                    this.parseDisplayState(String(args[10]));



                }



                if (args.length >= 12)



                {



                    this.parseWorldLoreState(String(args[11]));



                }



                if (args.length >= 13)



                {



                    this.parseExperimentalState(String(args[12]));



                }



                if (args.length >= 14)



                {



                    this.parseDirectorState(String(args[13]));



                }



                this.selectTab(6);



                return;



            }



            if (cmd == "director")



            {



                this.setModal(true);



                if (args.length >= 3)



                {



                    var dId:String = String(args[1]);



                    var dName:String = String(args[2]);



                    var dLore:String = (args.length > 3) ? String(args[3]) : "00";



                    this.onLoreDataCommand([dId, dName, dLore]);



                }



                if (args.length >= 5)



                {



                    this.parseContextState(String(args[4]));



                    this.rebuildContextItems();



                }



                if (args.length >= 6)



                {



                    this.mAutonomyEnabled = (String(args[5]) == "1" || String(args[5]).toLowerCase() == "true");



                }



                if (args.length >= 7)



                {



                    var pIntD:int = parseInt(String(args[6]));



                    if (pIntD > 0) this.mAutonomyInterval = pIntD;



                }



                if (args.length >= 8)



                {



                    this.parseGenealogyState(String(args[7]));



                }



                if (args.length >= 9)



                {



                    this.parseMemoryState(String(args[8]));



                }



                if (args.length >= 10)



                {



                    this.parseModsState(String(args[9]));



                }



                if (args.length >= 11)



                {



                    this.parseDisplayState(String(args[10]));



                }



                if (args.length >= 12)



                {



                    this.parseWorldLoreState(String(args[11]));



                }



                if (args.length >= 13)



                {



                    this.parseExperimentalState(String(args[12]));



                }



                if (args.length >= 14)



                {



                    this.parseDirectorState(String(args[13]));



                }



                this.selectTab(7);



                return;



            }



            if (cmd == "worlds" || cmd == "world_lore")



            {



                this.setModal(true);



                if (args.length >= 3)



                {



                    var wId:String = String(args[1]);



                    var wName:String = String(args[2]);



                    var wLore:String = (args.length > 3) ? String(args[3]) : "00";



                    this.onLoreDataCommand([wId, wName, wLore]);



                }



                if (args.length >= 5)



                {



                    this.parseContextState(String(args[4]));



                    this.rebuildContextItems();



                }



                if (args.length >= 6)



                {



                    this.mAutonomyEnabled = (String(args[5]) == "1" || String(args[5]).toLowerCase() == "true");



                }



                if (args.length >= 7)



                {



                    var pIntW:int = parseInt(String(args[6]));



                    if (pIntW > 0) this.mAutonomyInterval = pIntW;



                }



                if (args.length >= 8)



                {



                    this.parseGenealogyState(String(args[7]));



                }



                if (args.length >= 9)



                {



                    this.parseMemoryState(String(args[8]));



                }



                if (args.length >= 10)



                {



                    this.parseModsState(String(args[9]));



                }



                if (args.length >= 11)



                {



                    this.parseDisplayState(String(args[10]));



                }



                if (args.length >= 12)



                {



                    this.parseWorldLoreState(String(args[11]));



                }



                if (args.length >= 13)



                {



                    this.parseExperimentalState(String(args[12]));



                }



                if (args.length >= 14)



                {



                    this.parseDirectorState(String(args[13]));



                }



                this.selectTab(9);



                return;



            }



            if (cmd == "world_saved")



            {



                this.onWorldSavedCommand(args);



                return;



            }



            if (cmd == "world_cleared")



            {



                this.onWorldClearedCommand(args);



                return;



            }



            if (cmd == "experimental")



            {



                this.setModal(true);



                if (args.length >= 3)



                {



                    var expId:String = String(args[1]);



                    var expName:String = String(args[2]);



                    var expLore:String = (args.length > 3) ? String(args[3]) : "00";



                    this.onLoreDataCommand([expId, expName, expLore]);



                }



                if (args.length >= 5)



                {



                    this.parseContextState(String(args[4]));



                    this.rebuildContextItems();



                }



                if (args.length >= 6)



                {



                    this.mAutonomyEnabled = (String(args[5]) == "1" || String(args[5]).toLowerCase() == "true");



                }



                if (args.length >= 7)



                {



                    var pIntExp:int = parseInt(String(args[6]));



                    if (pIntExp > 0) this.mAutonomyInterval = pIntExp;



                }



                if (args.length >= 8)



                {



                    this.parseGenealogyState(String(args[7]));



                }



                if (args.length >= 9)



                {



                    this.parseMemoryState(String(args[8]));



                }



                if (args.length >= 10)



                {



                    this.parseModsState(String(args[9]));



                }



                if (args.length >= 11)



                {



                    this.parseDisplayState(String(args[10]));



                }



                if (args.length >= 12)



                {



                    this.parseWorldLoreState(String(args[11]));



                }



                if (args.length >= 13)



                {



                    this.parseExperimentalState(String(args[12]));



                }



                if (args.length >= 14)



                {



                    this.parseDirectorState(String(args[13]));



                }



                this.selectTab(10);



                return;



            }



                        if (cmd == "multisim_rule")

            {

                var rKey:String = String(args[1]);

                var rVal:String = (args.length > 2) ? this.decodeSafeStr(String(args[2])) : "";

                this.mMultisimRules[rKey] = rVal;

                if (this.mActiveMultisimRuleKey == rKey && this.mMultisimRuleInput != null)

                {

                    this.mMultisimRuleInput.text = rVal;

                }

                return;

            }



            if (cmd == "gene_sync")



            {



                if (args.length >= 2)



                {



                    this.parseGenealogyState(String(args[1]));



                    this.rebuildGenealogyItems();



                }



                return;



            }



            if (cmd == "mem_sync")



            {



                if (args.length >= 2)



                {



                    this.parseMemoryState(String(args[1]));



                    this.rebuildMemoryItems();



                }



                return;



            }



            if (cmd == "mods_sync")



            {



                if (args.length >= 2)



                {



                    this.parseModsState(String(args[1]));



                    this.rebuildModsItems();



                }



                return;



            }



            if (cmd == "disp_sync")



            {



                if (args.length >= 2)



                {



                    this.parseDisplayState(String(args[1]));



                    this.rebuildDisplayItems();



                }



                return;



            }



            if (cmd == "exp_sync")



            {



                if (args.length >= 2)



                {



                    this.parseExperimentalState(String(args[1]));



                    this.rebuildExperimentalItems();



                }



                return;



            }



            if (cmd == "dir_sync" || cmd == "director_sync")



            {



                if (args.length >= 2)



                {



                    this.parseDirectorState(String(args[1]));



                    this.refreshDirectorUI();



                }



                return;



            }



            if (cmd == "ctx_sync")



            {



                if (args.length >= 2)



                {



                    this.parseContextState(String(args[1]));



                    this.rebuildContextItems();



                }



                return;



            }



        }



        this.setModal(true);



        this.selectTab(0);



    }



    private var mOpenDropdown:Object = null;



    public function setOpenDropdown(dd:Object):void



    {



        this.mOpenDropdown = dd;



    }



    public function closeActivePopup():void



    {



        if (this.mOpenDropdown != null)



        {



            var d:Object = this.mOpenDropdown;



            this.mOpenDropdown = null;



            try



            {



                d.closePopup();



            }



            catch (errClose:Error) {}



        }



    }



    public static function sendSetting(key:String, value:*):void



    {



        if (ExternalInterface.available)



        {



            ExternalInterface.call("CallGameService", "PostServerCommand", {



                "command": "synapse.save_setting",



                "commandArgs": [String(key), String(value)]



            }, false);



        }



    }



    private function sampleCurve(arr:Array, progress:Number):Number



    {



        var maxIdx:int = arr.length - 1;



        var pos:Number = progress * maxIdx;



        var idx:int = int(Math.floor(pos));



        if (idx < 0)



        {



            idx = 0;



        }



        if (idx >= maxIdx)



        {



            return Number(arr[maxIdx]);



        }



        var frac:Number = pos - idx;



        var v0:Number = Number(arr[idx]);



        var v1:Number = Number(arr[idx + 1]);



        return v0 + (v1 - v0) * frac;



    }



    private function applyWindowTransform(sx:Number, sy:Number, winAlpha:Number, dimAlpha:Number):void



    {



        if (this.mWindow)



        {



            this.mWindow.scaleX = sx;



            this.mWindow.scaleY = sy;



            this.mWindow.alpha = winAlpha;



            this.mWindow.x = Math.round(this.mBaseX + (WIN_W * (1.0 - sx)) * 0.5);



            this.mWindow.y = Math.round(this.mBaseY + (WIN_H * (1.0 - sy)) * 0.5);



        }



        if (this.mDimmer)



        {



            this.mDimmer.alpha = dimAlpha;



        }



    }



    private function onAnimFrame(e:Event):void



    {



        var elapsed:Number = getTimer() - this.mAnimStart;



        if (this.mAnimMode == 1)



        {



            var pOpen:Number = elapsed / 300.0;



            if (pOpen >= 1.0)



            {



                removeEventListener(Event.ENTER_FRAME, this.onAnimFrame);



                this.mAnimMode = 0;



                this.applyWindowTransform(1.0, 1.0, 1.0, 1.0);



            }



            else



            {



                var sy:Number = this.sampleCurve(this.mOpenSy, pOpen);



                var al:Number = this.sampleCurve(this.mOpenAlpha, pOpen);



                var dimAl:Number = pOpen * 3.2;



                if (dimAl > 1.0)



                {



                    dimAl = 1.0;



                }



                this.applyWindowTransform(1.0, sy, al, dimAl);



            }



        }



        else if (this.mAnimMode == 2)



        {



            var pClose:Number = elapsed / 190.0;



            if (pClose >= 1.0)



            {



                removeEventListener(Event.ENTER_FRAME, this.onAnimFrame);



                this.mAnimMode = 0;



                this.visible = false;



                this.applyWindowTransform(1.0, 1.0, 1.0, 1.0);



                // text input capture



            }



            else



            {



                var sc:Number = this.sampleCurve(this.mCloseScale, pClose);



                var alClose:Number = this.sampleCurve(this.mCloseAlpha, pClose);



                var dimClose:Number = 1.0 - pClose;



                if (dimClose < 0.0)



                {



                    dimClose = 0.0;



                }



                this.applyWindowTransform(sc, sc, alClose, dimClose);



            }



        }



        else



        {



            removeEventListener(Event.ENTER_FRAME, this.onAnimFrame);



        }



    }



    public function setModal(active:Boolean):void



    {



        if (active)



        {



            removeEventListener(Event.ENTER_FRAME, this.onAnimFrame);



            this.hideStudioPanel();



            if (this.mWindow != null) this.mWindow.visible = true;



            if (this.mDimmer != null) this.mDimmer.visible = true;



            this.visible = true;



            this.mouseEnabled = true;



            this.mouseChildren = true;



            try



            {



                if (this.parent)



                {



                    this.parent.setChildIndex(this, this.parent.numChildren - 1);



                }



            }



            catch (errZ:Error) {}



            this.drawDimmer();



            this.centerWindow();



            // Перехват клавиши ESC на время открытого окна, чтобы не открывалось меню паузы игры



            // text input capture



            this.grabStageFocus();



            // Запуск фирменной пружинной анимации раскрытия из центра по вертикали (1:1 Sims 4)



            this.mAnimMode = 1;



            this.mAnimStart = getTimer();



            this.applyWindowTransform(1.0, 0.531, 0.82, 0.25);



            addEventListener(Event.ENTER_FRAME, this.onAnimFrame);



            try



            {



                var cm:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cm.CallUIService("SetWidgetModality", {



                    "widgetName": "FacebookDisplay",



                    "bOn": true



                });



            }



            catch (errOn:Error) {}



        }



        else



        {



            this.closeActivePopup();



            this.closeDirectorModal();



            this.mouseEnabled = false;



            this.mouseChildren = false;



            this.dropStageFocus();



            if (this.visible && this.mAnimMode != 2)



            {



                removeEventListener(Event.ENTER_FRAME, this.onAnimFrame);



                this.mAnimMode = 2;



                this.mAnimStart = getTimer();



                addEventListener(Event.ENTER_FRAME, this.onAnimFrame);



            }



            else if (!this.visible)



            {



                this.mAnimMode = 0;



                // text input capture



            }



            try



            {



                var cm2:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cm2.CallUIService("SetWidgetModality", {



                    "widgetName": "FacebookDisplay",



                    "bOn": false



                });



                try {



                    cm2.CallGameService("SetTextFieldInput", false);



                } catch(eStf:Error) {}



            }



            catch (errOff:Error) {}



            if (ExternalInterface.available)



            {



                ExternalInterface.call("CallGameService", "PostServerCommand", {



                    "command": "synapse.ui_closed",



                    "commandArgs": []



                }, false);



            }



        }



    }



    // =====================================================================



    // ОТРИСОВКА КАРКАСА ОКНА (ЧИСТАЯ ЗАЛИВКА БЕЗ lineStyle НА КРИВЫХ)



    // =====================================================================



    private function buildUI():void



    {



        this.mDimmer = new Sprite();



        this.drawDimmer();



        this.mDimmer.addEventListener(MouseEvent.CLICK, this.onDimmerClick);



        addChild(this.mDimmer);



        this.mWindow = new Sprite();



        this.mWindow.addEventListener(MouseEvent.MOUSE_DOWN, this.onWindowMouseDown);



        addChild(this.mWindow);



        this.drawWindowFrame();



        this.buildHeader();



        this.buildSidebar();



        this.buildWorkspace();



        this.selectTab(0);



    }



    private function onWindowMouseDown(e:MouseEvent):void



    {



        this.closeActivePopup();



        if (e && e.target is TextField && (e.target as TextField).type == "input")



        {



            var targetTf:TextField = e.target as TextField;



            if (stage) stage.focus = targetTf;



            try {



                var cmWm:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cmWm.CallGameService("SetTextFieldInput", true);



            } catch(eWm:Error) {}



            return;



        }



        try {



            var cmOut:Object = getDefinitionByName("olympus.io.CommunicationManager");



            cmOut.CallGameService("SetTextFieldInput", false);



        } catch(eOut:Error) {}



        this.grabStageFocus();



    }



    private function onDimmerClick(e:MouseEvent):void



    {



        this.closeActivePopup();



        this.setModal(false);



    }



    private function drawDimmer():void



    {



        if (!this.mDimmer) return;



        var sw:Number = stage ? stage.stageWidth : 2560;



        var sh:Number = stage ? stage.stageHeight : 1440;



        if (sw < 100)



        {



            sw = 2560;



        }



        if (sh < 100)



        {



            sh = 1440;



        }



        this.mDimmer.graphics.clear();



        // Точный цвет и плотность затемнения фона из оригинальных настроек The Sims 4 (#0A103D, alpha 0.46)



        this.mDimmer.graphics.beginFill(0x0A103D, 0.46);



        this.mDimmer.graphics.drawRect(-1000, -1000, sw + 2000, sh + 2000);



        this.mDimmer.graphics.endFill();



    }



    private function drawWindowFrame():void



    {



        // 0. Векторная многослойная тень вокруг всего окна (Scaleform игнорирует DropShadowFilter)



        var winShadow:Shape = new Shape();



        winShadow.graphics.beginFill(0x000000, 0.08);



        winShadow.graphics.drawRoundRect(-6, -2, WIN_W + 12, WIN_H + 12, 22, 22);



        winShadow.graphics.endFill();



        winShadow.graphics.beginFill(0x000000, 0.14);



        winShadow.graphics.drawRoundRect(-3, 0, WIN_W + 6, WIN_H + 7, 19, 19);



        winShadow.graphics.endFill();



        winShadow.graphics.beginFill(0x000000, 0.22);



        winShadow.graphics.drawRoundRect(-1, 1, WIN_W + 2, WIN_H + 3, 17, 17);



        winShadow.graphics.endFill();



        this.mWindow.addChild(winShadow);



        // 1. Чисто-белый главный корпус окна



        var mainBg:Shape = new Shape();



        mainBg.graphics.beginFill(0xFFFFFF, 1.0);



        mainBg.graphics.drawRoundRect(0, 0, WIN_W, WIN_H, 16, 16);



        mainBg.graphics.endFill();



        this.mWindow.addChild(mainBg);



        // 2. Нижняя металлическая панель футера (#AEB7CA -> #C8CED9 как в оригинале Sims 4)



        var footBg:Shape = new Shape();



        var footMat:Matrix = new Matrix();



        footMat.createGradientBox(WIN_W, FOOTER_H, Math.PI / 2, 0, WIN_H - FOOTER_H);



        footBg.graphics.beginGradientFill(



            GradientType.LINEAR,



            [COL_FOOTER_TOP, COL_FOOTER_BOT],



            [1.0, 1.0],



            [0, 255],



            footMat



        );



        footBg.graphics.drawRoundRect(0, WIN_H - FOOTER_H, WIN_W, FOOTER_H, 16, 16);



        footBg.graphics.endFill();



        this.mWindow.addChild(footBg);



        // Прямой верх футера и 2px переходная тень сверху футера (как в оригинале Sims 4)



        var footTopStrip:Shape = new Shape();



        footTopStrip.graphics.beginFill(COL_FOOTER_TOP, 1.0);



        footTopStrip.graphics.drawRect(0, WIN_H - FOOTER_H, WIN_W, 10);



        footTopStrip.graphics.endFill();



        footTopStrip.graphics.beginFill(0x9FA9BD, 1.0);



        footTopStrip.graphics.drawRect(0, WIN_H - FOOTER_H, WIN_W, 1);



        footTopStrip.graphics.endFill();



        footTopStrip.graphics.beginFill(0xA7B0C4, 1.0);



        footTopStrip.graphics.drawRect(0, WIN_H - FOOTER_H + 1, WIN_W, 1);



        footTopStrip.graphics.endFill();



        this.mWindow.addChild(footTopStrip);



    }



    private function buildHeader():void



    {



        // Зона перетаскивания за верхнюю часть окна



        var dragArea:Sprite = new Sprite();



        dragArea.graphics.beginFill(0x000000, 0.001);



        dragArea.graphics.drawRect(0, 0, WIN_W - 50, HEADER_H);



        dragArea.graphics.endFill();



        dragArea.buttonMode = true;



        dragArea.addEventListener(MouseEvent.MOUSE_DOWN, this.onDragStart);



        this.mWindow.addChild(dragArea);



        // Заголовок по центру окна (идеально центрированный нативный $TextFont)



        var title:TextField = makeCenteredText("НАСТРОЙКИ SYNAPSE", 21, COL_ROYAL_BLUE, WIN_W);



        title.x = 0;



        title.y = 17;



        this.mWindow.addChild(title);



        // Аккуратная круглая 3D-кнопка закрытия [X] справа вверху (22x22, как в оригинале Sims 4)



        this.mCloseBtn = new Sprite();



        this.mCloseBtn.buttonMode = true;



        this.mCloseBtn.mouseChildren = false;



        this.mCloseBtn.x = WIN_W - 32;



        this.mCloseBtn.y = 8;



        this.mCloseBg = new Shape();



        this.mCloseIcon = new Shape();



        this.mCloseBtn.addChild(this.mCloseBg);



        this.mCloseBtn.addChild(this.mCloseIcon);



        this.redrawCloseBtn(false);



        this.mCloseBtn.addEventListener(MouseEvent.ROLL_OVER, this.onCloseOver);



        this.mCloseBtn.addEventListener(MouseEvent.ROLL_OUT, this.onCloseOut);



        this.mCloseBtn.addEventListener(MouseEvent.CLICK, this.onCloseClick);



        this.mWindow.addChild(this.mCloseBtn);



    }



    private function onDragStart(e:MouseEvent):void



    {



        this.closeActivePopup();



        if (stage)



        {



            this.mDragging = true;



            this.mDragX = stage.mouseX - this.mWindow.x;



            this.mDragY = stage.mouseY - this.mWindow.y;



        }



    }



    private function redrawCloseBtn(hover:Boolean):void



    {



        if (!this.mCloseBg || !this.mCloseIcon) return;



        this.mCloseBg.graphics.clear();



        // 1. Векторная 3D-тень снизу (#D4D4D4 и #7F7F7F из попиксельного скана IMG1 Close Button)



        this.mCloseBg.graphics.beginFill(0x000000, 0.10);



        this.mCloseBg.graphics.drawCircle(11, 13, 11);



        this.mCloseBg.graphics.endFill();



        this.mCloseBg.graphics.beginFill(0x7F7F7F, 1.0);



        this.mCloseBg.graphics.drawCircle(11, 12, 11);



        this.mCloseBg.graphics.endFill();



        // 2. Внешний контур с вертикальным градиентом (#D4D4D4 сверху -> #AEAEAE по бокам -> #7F7F7F снизу)



        var bMat:Matrix = new Matrix();



        bMat.createGradientBox(22, 22, Math.PI / 2, 0, 0);



        this.mCloseBg.graphics.beginGradientFill(GradientType.LINEAR, [0xD4D4D4, 0xAEAEAE, 0x7F7F7F], [1.0, 1.0, 1.0], [0, 160, 255], bMat);



        this.mCloseBg.graphics.drawCircle(11, 11, 11);



        this.mCloseBg.graphics.endFill();



        // 3. Верхний белый 1px блик внутри



        this.mCloseBg.graphics.beginFill(0xFFFFFF, 1.0);



        this.mCloseBg.graphics.drawCircle(11, 10.6, 10);



        this.mCloseBg.graphics.endFill();



        // 4. Внутренний выпуклый серебристо-белый градиент (высветляется при наведении, как в оригинале Sims 4)



        var mat:Matrix = new Matrix();



        mat.createGradientBox(20, 20, Math.PI / 2, 1, 1);



        var topC:uint = 0xFFFFFF;



        var midC:uint = hover ? 0xFFFFFF : 0xF5F5F5;



        var botC:uint = hover ? 0xF0F0F0 : 0xDFDFDF;



        this.mCloseBg.graphics.beginGradientFill(GradientType.LINEAR, [topC, midC, botC], [1.0, 1.0, 1.0], [0, 140, 255], mat);



        this.mCloseBg.graphics.drawCircle(11, 11, 9.8);



        this.mCloseBg.graphics.endFill();



        // 5. Чёткий крестик внутри (синий #1149A0, при наведении становится зелёным #35B212 как в Sims 4)



        this.mCloseIcon.graphics.clear();



        this.mCloseIcon.graphics.lineStyle(2.2, hover ? COL_HOVER_GREEN : 0x1149A0, 1.0);



        this.mCloseIcon.graphics.moveTo(7.5, 7.5);



        this.mCloseIcon.graphics.lineTo(14.5, 14.5);



        this.mCloseIcon.graphics.moveTo(14.5, 7.5);



        this.mCloseIcon.graphics.lineTo(7.5, 14.5);



    }



    private function onCloseOver(e:MouseEvent):void



    {



        this.redrawCloseBtn(true);



    }



    private function onCloseOut(e:MouseEvent):void



    {



        this.redrawCloseBtn(false);



    }



    private function onCloseClick(e:MouseEvent):void



    {



        this.setModal(false);



    }



    // =====================================================================



    // ЛЕВАЯ КОЛОНКА ВКЛАДОК (1:1 КАК В "НАСТРОЙКИ ИГРЫ")



    // =====================================================================



    private function buildSidebar():void



    {



        var tabH:Number = 39;



        var gap:Number = 2;



        for (var i:int = 0; i < this.mTabTitles.length; i++)



        {



            var tab:SidebarTab = new SidebarTab(i, String(this.mTabTitles[i]), SIDEBAR_W, tabH, this);



            tab.x = 0;



            tab.y = HEADER_H + i * (tabH + gap);



            this.mWindow.addChild(tab);



            this.mTabs.push(tab);



        }



    }



    // =====================================================================



    // ПРАВАЯ ОБЛАСТЬ (БЕЗ lineStyle — 100% ГЛАДКИЕ УГЛЫ И РАМКИ)



    // =====================================================================



    private function drawSectionContainerOn(targetCont:Sprite, yPos:Number, widthVal:Number, barH:Number, bodyH:Number):void



    {



        var totalH:Number = barH + bodyH;



        var borderShape:Shape = new Shape();



        borderShape.graphics.beginFill(COL_BOX_BORDER, 1.0);



        borderShape.graphics.drawRoundRect(0, yPos, widthVal, totalH, 8, 8);



        borderShape.graphics.endFill();



        targetCont.addChild(borderShape);



        var innerWhite:Shape = new Shape();



        innerWhite.graphics.beginFill(0xFFFFFF, 1.0);



        innerWhite.graphics.drawRoundRect(1, yPos + 1, widthVal - 2, totalH - 2, 6, 6);



        innerWhite.graphics.endFill();



        targetCont.addChild(innerWhite);



        var hdrShape:Shape = new Shape();



        hdrShape.graphics.beginFill(COL_SEC_HEADER, 1.0);



        hdrShape.graphics.drawRoundRect(0, yPos, widthVal, barH, 6, 6);



        hdrShape.graphics.endFill();



        targetCont.addChild(hdrShape);



        var hdrFlatBot:Shape = new Shape();



        hdrFlatBot.graphics.beginFill(COL_SEC_HEADER, 1.0);



        hdrFlatBot.graphics.drawRect(0, yPos + barH - 5, widthVal, 5);



        hdrFlatBot.graphics.endFill();



        targetCont.addChild(hdrFlatBot);



    }



    private function drawSectionContainer(yPos:Number, widthVal:Number, barH:Number, bodyH:Number):void



    {



        var totalH:Number = barH + bodyH;



        // 1. Внешняя рамка секции через чистую заливку (1px вокруг)



        var borderShape:Shape = new Shape();



        borderShape.graphics.beginFill(COL_BOX_BORDER, 1.0);



        borderShape.graphics.drawRoundRect(0, yPos, widthVal, totalH, 8, 8);



        borderShape.graphics.endFill();



        this.mWorkspace.addChild(borderShape);



        // 2. Внутренний белый фон секции (отступ 1px)



        var innerWhite:Shape = new Shape();



        innerWhite.graphics.beginFill(0xFFFFFF, 1.0);



        innerWhite.graphics.drawRoundRect(1, yPos + 1, widthVal - 2, totalH - 2, 6, 6);



        innerWhite.graphics.endFill();



        this.mWorkspace.addChild(innerWhite);



        // 3. Серо-стальная шапка секции сверху



        var hdrShape:Shape = new Shape();



        hdrShape.graphics.beginFill(COL_SEC_HEADER, 1.0);



        hdrShape.graphics.drawRoundRect(0, yPos, widthVal, barH, 6, 6);



        hdrShape.graphics.endFill();



        this.mWorkspace.addChild(hdrShape);



        // Прямой нижний край серой шапки



        var hdrFlatBot:Shape = new Shape();



        hdrFlatBot.graphics.beginFill(COL_SEC_HEADER, 1.0);



        hdrFlatBot.graphics.drawRect(0, yPos + barH - 5, widthVal, 5);



        hdrFlatBot.graphics.endFill();



        this.mWorkspace.addChild(hdrFlatBot);



    }



    // =========================================================================



    // LORE AS3 HELPERS & COMMAND RECEIVERS



    // =========================================================================



    private function decodeSafeStr(s:String):String



    {



        if (!s || s == "00") return "";



        try {



            return decodeURIComponent(s);



        } catch(e:Error) {



            return s;



        }



        return s;



    }



    private function encodeSafeStr(s:String):String



    {



        if (!s || s.length == 0) return "00";



        try {



            return encodeURIComponent(s);



        } catch(e:Error) {



            return escape(s);



        }



        return "00";



    }



    public function onLoreDataCommand(args:Array):void



    {



        if (!args || args.length < 2) return;



        this.mCurrentSimId = String(args[0]);



        var simName:String = this.decodeSafeStr(String(args[1]));



        var loreText:String = (args.length > 2) ? this.decodeSafeStr(String(args[2])) : "";



        var raceText:String = (args.length > 3) ? this.decodeSafeStr(String(args[3])) : "";



        this.mCurrentSimName = simName;



        this.mCurrentLoreText = loreText;



        this.mCurrentRaceText = raceText;



        if (this.mSelectedSimLabel) {



            this.mSelectedSimLabel.text = "Персонаж: " + simName + " [ID: " + this.mCurrentSimId + "]";



        }



        if (this.mLoreInput) {



            this.mLoreInput.text = loreText;



        }



        if (this.mLoreRaceInput) {



            this.mLoreRaceInput.text = raceText;



        }



        if (this.mLoreSavedBadge) {



            this.mLoreSavedBadge.visible = false;



        }



        this.updateLoreCounter();



    }



    public function onLoreSavedCommand(args:Array):void



    {



        if (this.mLoreSavedBadge) {



            this.mLoreSavedBadge.text = "Сохранено в памяти ИИ!";



            this.mLoreSavedBadge.visible = true;



        }



        this.updateLoreCounter();



    }



    public function onLoreClearedCommand(args:Array):void



    {



        if (this.mLoreInput) {



            this.mLoreInput.text = "";



        }



        if (this.mLoreRaceInput) {



            this.mLoreRaceInput.text = "";



        }



        if (this.mLoreSavedBadge) {



            this.mLoreSavedBadge.text = "Лор очищен!";



            this.mLoreSavedBadge.visible = true;



        }



        this.updateLoreCounter();



    }



    public function updateLoreCounter():void



    {



        var len:int = (this.mLoreInput && this.mLoreInput.text) ? this.mLoreInput.text.length : 0;



        if (this.mLoreCounter) {



            this.mLoreCounter.text = "Символов: " + len + " / 2000";



        }



        if (this.mLoreStatusLabel) {



            if (len > 0) {



                this.mLoreStatusLabel.htmlText = "<font color='#2A6B9C'>Лор активен:</font> задан индивидуальный характер (" + len + " симв.)";



            } else {



                this.mLoreStatusLabel.htmlText = "<font color='#8A9BA8'>Индивидуальный лор не задан (используется базовый характер)</font>";



            }



        }



    }



    // =========================================================================



    // CONTEXT SETTINGS SECTION & LOGIC



    // =========================================================================



    public function parseContextState(rawStr:String):void



    {



        if (!rawStr || rawStr.length == 0 || rawStr == "00") return;



        var pairs:Array = rawStr.split(";");



        for (var i:int = 0; i < pairs.length; i++)



        {



            var pStr:String = String(pairs[i]);



            if (pStr.indexOf(":") != -1)



            {



                var kv:Array = pStr.split(":");



                var k:String = String(kv[0]);



                var v:String = String(kv[1]);



                this.mContextFlagsState[k] = (v == "1");



            }



        }



    }



    public function parseGenealogyState(rawStr:String):void



    {



        if (!rawStr || rawStr.length == 0 || rawStr == "00") return;



        var pairs:Array = rawStr.split(";");



        for (var i:int = 0; i < pairs.length; i++)



        {



            var pStr:String = String(pairs[i]);



            if (pStr.indexOf(":") != -1)



            {



                var kv:Array = pStr.split(":");



                var k:String = String(kv[0]);



                var v:String = String(kv[1]);



                if (k == "depth")



                {



                    var dVal:int = parseInt(v);



                    if (dVal >= 0) this.mGenealogyDepth = dVal;



                }



                else if (k == "max_relatives")



                {



                    // reserved



                }



                else



                {



                    this.mGenealogyFlagsState[k] = (v == "1");



                }



            }



        }



    }



    public function buildContextSection():void



    {



        this.mContextContainer = new Sprite();



        this.mContextContainer.visible = false;



        this.mWorkspace.addChild(this.mContextContainer);



        var secW:Number = WORKSPACE_W;



        var barH:Number = 28;



        // Секция 1: Выбор режима



        var sec1Y:Number = 0;



        var sec1BodyH:Number = 80;



        this.drawSectionContainerOn(this.mContextContainer, sec1Y, secW, barH, sec1BodyH);



        var sec1Title:TextField = makeCenteredText("ВЫБОР РЕЖИМА ДЛЯ НАСТРОЙКИ КОНТЕКСТА", 13, 0xFFFFFF, secW);



        sec1Title.x = 0;



        sec1Title.y = sec1Y + 4;



        this.mContextContainer.addChild(sec1Title);



        // 4 кнопки выбора режима (с интерактивной подсветкой и Maxis-стилем)



        var modes:Array = [



            {"id": "thought", "title": "ЧТЕНИЕ МЫСЛЕЙ"},



            {"id": "messenger", "title": "МЕССЕНДЖЕР"},



            {"id": "direct", "title": "ЖИВОЕ ОБЩЕНИЕ"},



            {"id": "intimate", "title": "ИНТИМ-ОБЩЕНИЕ"}



        ];



        this.mModeBtns = [];



        var btnW:Number = 158;



        var btnH:Number = 30;



        var btnStartX:Number = 12;



        var btnGap:Number = 8;



        var selfRef:SettingsUI = this;



        for (var mIdx:int = 0; mIdx < modes.length; mIdx++)



        {



            var mObj:Object = modes[mIdx];



            var mBtn:Sprite = new Sprite();



            mBtn.name = String(mObj.id);



            mBtn.buttonMode = true;



            mBtn.useHandCursor = true;



            mBtn.mouseChildren = false;



            mBtn.x = btnStartX + mIdx * (btnW + btnGap);



            mBtn.y = sec1Y + barH + 8;



            var mBg:Shape = new Shape();



            mBtn.addChild(mBg);



            var mTf:TextField = makeCenteredText(String(mObj.title), 11, COL_ROYAL_BLUE, btnW);



            mTf.y = 6;



            mBtn.addChild(mTf);



            this.drawModeBtn(mBtn, mObj.id == "thought", false);



            mBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



                var targetBtn:Sprite = e.currentTarget as Sprite;



                if (targetBtn != null)



                {



                    selfRef.setContextMode(targetBtn.name);



                }



            });



            mBtn.addEventListener(MouseEvent.ROLL_OVER, function(e:MouseEvent):void {



                var targetBtn:Sprite = e.currentTarget as Sprite;



                if (targetBtn != null)



                {



                    selfRef.drawModeBtn(targetBtn, targetBtn.name == selfRef.mCurrentContextMode, true);



                }



            });



            mBtn.addEventListener(MouseEvent.ROLL_OUT, function(e:MouseEvent):void {



                var targetBtn:Sprite = e.currentTarget as Sprite;



                if (targetBtn != null)



                {



                    selfRef.drawModeBtn(targetBtn, targetBtn.name == selfRef.mCurrentContextMode, false);



                }



            });



            this.mContextContainer.addChild(mBtn);



            this.mModeBtns.push(mBtn);



        }



        // Полоса-подсказка выбранного режима



        var hintBg:Shape = new Shape();



        var hMat:Matrix = new Matrix();



        hMat.createGradientBox(secW - 24, 28, Math.PI / 2, 0, 0);



        hintBg.graphics.beginGradientFill(



            GradientType.LINEAR,



            [0xECF3FA, 0xDFEAF4],



            [1.0, 1.0],



            [0, 255],



            hMat



        );



        hintBg.graphics.lineStyle(1, 0xB8CBDC, 0.8, true);



        hintBg.graphics.drawRoundRect(12, sec1Y + barH + 44, secW - 24, 28, 6, 6);



        hintBg.graphics.endFill();



        this.mContextContainer.addChild(hintBg);



        this.mContextHintTf = makeText("", 11, 0x1E466B);



        this.mContextHintTf.x = 22;



        this.mContextHintTf.y = sec1Y + barH + 50;



        this.mContextContainer.addChild(this.mContextHintTf);



        // Секция 2: Компоненты контекста



        var sec2Y:Number = sec1Y + barH + sec1BodyH + 10;



        var sec2BodyH:Number = 320;



        this.drawSectionContainerOn(this.mContextContainer, sec2Y, secW, barH, sec2BodyH);



        var sec2Title:TextField = makeCenteredText("КОМПОНЕНТЫ КОНТЕКСТА (ВКЛ / ВЫКЛ)", 13, 0xFFFFFF, secW);



        sec2Title.x = 0;



        sec2Title.y = sec2Y + 4;



        this.mContextContainer.addChild(sec2Title);



        // Верхняя панель действий: Аккуратные кнопки ВКЛЮЧИТЬ ВСЕ, ВЫКЛЮЧИТЬ ВСЕ, ПО УМОЛЧАНИЮ



        // 1. Скролл-контейнер MaxisScrollView для секций-аккордеонов (нижний слой)



        var scrollW:Number = secW - 24;



        var scrollH:Number = sec2BodyH - 46;



        this.mContextScrollView = new MaxisScrollView(scrollW, scrollH);



        this.mContextScrollView.x = 12;



        this.mContextScrollView.y = sec2Y + barH + 40;



        this.mContextContainer.addChild(this.mContextScrollView);



        // 2. Верхняя защитная панель действий (верхний слой с непрозрачной подложкой)



        var topControlsBar:Sprite = new Sprite();



        var topBarBg:Shape = new Shape();



        topBarBg.graphics.beginFill(0xFFFFFF, 1.0);



        topBarBg.graphics.drawRect(1, sec2Y + barH + 1, secW - 2, 38);



        topBarBg.graphics.endFill();



        topControlsBar.addChild(topBarBg);



        var bulkAllOnBtn:SimsPillButton = new SimsPillButton("ВКЛЮЧИТЬ ВСЕ", 132, 26, "bulk_on", "", this, false, 11);



        bulkAllOnBtn.x = 12;



        bulkAllOnBtn.y = sec2Y + barH + 8;



        bulkAllOnBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.onBulkActionClick("enable_all");



        });



        topControlsBar.addChild(bulkAllOnBtn);



        var bulkAllOffBtn:SimsPillButton = new SimsPillButton("ВЫКЛЮЧИТЬ ВСЕ", 136, 26, "bulk_off", "", this, false, 11);



        bulkAllOffBtn.x = 152;



        bulkAllOffBtn.y = sec2Y + barH + 8;



        bulkAllOffBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.onBulkActionClick("disable_all");



        });



        topControlsBar.addChild(bulkAllOffBtn);



        var bulkResetBtn:SimsPillButton = new SimsPillButton("ПО УМОЛЧАНИЮ", 132, 26, "bulk_reset", "", this, false, 11);



        bulkResetBtn.x = 296;



        bulkResetBtn.y = sec2Y + barH + 8;



        bulkResetBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.onBulkActionClick("reset_defaults");



        });



        topControlsBar.addChild(bulkResetBtn);



        this.mContextContainer.addChild(topControlsBar);



        // 3. Нижняя защитная белая плашка контейнера



        var bottomCap:Shape = new Shape();



        bottomCap.graphics.beginFill(0xFFFFFF, 1.0);



        bottomCap.graphics.drawRoundRect(1, sec2Y + barH + sec2BodyH - 8, secW - 2, 7, 4, 4);



        bottomCap.graphics.endFill();



        this.mContextContainer.addChild(bottomCap);



        this.setContextMode("thought");



    }



    public function drawModeBtn(btn:Sprite, isSelected:Boolean, isHover:Boolean):void



    {



        var bg:Shape = btn.getChildAt(0) as Shape;



        var tf:TextField = btn.getChildAt(1) as TextField;



        if (bg == null || tf == null) return;



        bg.graphics.clear();



        var btnW:Number = 158;



        var btnH:Number = 30;



        var bMat:Matrix = new Matrix();



        bMat.createGradientBox(btnW, btnH, Math.PI / 2, 0, 0);



        if (isSelected)



        {



            // Зелёный объёмный градиент Maxis The Sims 4



            bg.graphics.beginFill(0x000000, 0.08);



            bg.graphics.drawRoundRect(0, 2, btnW, btnH, 8, 8);



            bg.graphics.endFill();



            bg.graphics.beginGradientFill(



                GradientType.LINEAR,



                [0x68C430, 0x429D1E, 0x24780E],



                [1.0, 1.0, 1.0],



                [0, 160, 255],



                bMat



            );



            bg.graphics.drawRoundRect(0, 0, btnW, btnH, 8, 8);



            bg.graphics.endFill();



            bg.graphics.beginFill(0xFFFFFF, isHover ? 0.35 : 0.22);



            bg.graphics.drawRoundRect(1, 1, btnW - 2, 10, 7, 7);



            bg.graphics.endFill();



            tf.textColor = 0xFFFFFF;



        }



        else



        {



            // Серебристый неактивный таб Maxis



            bg.graphics.beginFill(0x000000, 0.04);



            bg.graphics.drawRoundRect(0, 2, btnW, btnH, 8, 8);



            bg.graphics.endFill();



            var borderCol:uint = isHover ? 0x4A83BD : 0xB0BFCF;



            bg.graphics.beginFill(borderCol, 1.0);



            bg.graphics.drawRoundRect(0, 0, btnW, btnH, 8, 8);



            bg.graphics.endFill();



            var topCol:uint = isHover ? 0xF8FAFD : 0xEFF3F8;



            var botCol:uint = isHover ? 0xDCE5EF : 0xD2DDE8;



            bg.graphics.beginGradientFill(



                GradientType.LINEAR,



                [topCol, botCol],



                [1.0, 1.0],



                [0, 255],



                bMat



            );



            bg.graphics.drawRoundRect(1, 1, btnW - 2, btnH - 2, 7, 7);



            bg.graphics.endFill();



            tf.textColor = isHover ? 0x0A63A5 : COL_ROYAL_BLUE;



        }



    }



    public function setContextMode(mode:String):void



    {



        this.mCurrentContextMode = mode;



        for (var i:int = 0; i < this.mModeBtns.length; i++)



        {



            var btn:Sprite = this.mModeBtns[i] as Sprite;



            if (btn != null)



            {



                this.drawModeBtn(btn, btn.name == mode, false);



            }



        }



        if (this.mContextHintTf)



        {



            if (mode == "thought")



                this.mContextHintTf.text = "Генерация внутренних мыслей симов в облачках над головой.";



            else if (mode == "messenger")



                this.mContextHintTf.text = "Генерация сообщений и переписок в смартфоне и соцсетях.";



            else if (mode == "direct")



                this.mContextHintTf.text = "Генерация реплик и реакций в прямом диалоге между симами.";



            else if (mode == "intimate")



                this.mContextHintTf.text = "Генерация реплик и мыслей в моменты физической близости.";



        }



        this.rebuildContextItems();



    }



    public function reflowAccordions():void



    {



        var currY:Number = 0;



        var gap:Number = 6;



        for (var i:int = 0; i < this.mAccordionSections.length; i++)



        {



            var sec:MaxisAccordionSection = this.mAccordionSections[i] as MaxisAccordionSection;



            if (sec != null)



            {



                sec.y = currY;



                currY += sec.getTotalHeight() + gap;



            }



        }



        if (this.mContextScrollView != null)



        {



            this.mContextScrollView.updateLayout(currY);



        }



    }



    public function rebuildContextItems():void



    {



        if (!this.mContextScrollView) return;



        var prevScroll:Number = this.mContextScrollView.getScrollY();



        var scrollContent:Sprite = this.mContextScrollView.getContent();



        while (scrollContent.numChildren > 0)



        {



            scrollContent.removeChildAt(0);



        }



        this.mAccordionSections = [];



        this.mCheckboxesByKey = {};



        var groups:Array = this.getContextGroupsForCurrentMode();



        var secW:Number = this.mContextScrollView.getViewportWidth();



        var selfRef:SettingsUI = this;



        for (var gIdx:int = 0; gIdx < groups.length; gIdx++)



        {



            var grp:Object = groups[gIdx];



            var secTitle:String = String(grp.title);



            var secKey:String = this.mCurrentContextMode + "_" + secTitle;



            var isInitiallyExpanded:Boolean = (this.mExpandedSections[secKey] !== undefined) ?



                Boolean(this.mExpandedSections[secKey]) : (gIdx == 0);



            var accSec:MaxisAccordionSection = new MaxisAccordionSection(



                secTitle,



                secW,



                28,



                isInitiallyExpanded,



                function(tSec:MaxisAccordionSection):void {



                    var k:String = selfRef.mCurrentContextMode + "_" + tSec.title;



                    selfRef.mExpandedSections[k] = tSec.isExpanded;



                    selfRef.reflowAccordions();



                }



            );



            var grpItems:Array = grp.items as Array;



            if (grpItems != null)



            {



                this.populateSectionItems(accSec.content, grpItems, secW);



            }



            scrollContent.addChild(accSec);



            this.mAccordionSections.push(accSec);



        }



        this.mContextScrollView.setOwnerSections(this.mAccordionSections);



        this.reflowAccordions();



        if (prevScroll > 0)



        {



            this.mContextScrollView.scrollTo(prevScroll);



        }



        else



        {



            this.mContextScrollView.resetScroll();



        }



    }



    private function populateSectionItems(container:Sprite, items:Array, secW:Number):void



    {



        var rowH:Number = 40;



        var selfRef:SettingsUI = this;



        for (var i:int = 0; i < items.length; i++)



        {



            var item:Object = items[i];



            var row:Sprite = new Sprite();



            row.y = i * rowH;



            row.buttonMode = true;



            row.useHandCursor = true;



            row.mouseChildren = true;



            // Фоновый слой (0.001 alpha для 100% захвата кликов по всей площади)



            var rowBg:Shape = new Shape();



            rowBg.graphics.beginFill(0xFFFFFF, 0.001);



            rowBg.graphics.drawRect(0, 0, secW, rowH);



            rowBg.graphics.endFill();



            row.addChild(rowBg);



            // Нижний аккуратный Maxis разделитель строки



            var sep:Shape = new Shape();



            sep.graphics.lineStyle(1, 0xCBD6E2, 0.40);



            sep.graphics.moveTo(16, rowH - 1);



            sep.graphics.lineTo(secW - 16, rowH - 1);



            row.addChild(sep);



            // Текст названия настройки



                        var titleTf:TextField = makeBoundedText(String(item.title), 12, 0x19456B, secW - 75);



            titleTf.x = 20;



            titleTf.y = 4;



            row.addChild(titleTf);



            // Описание опции



            var descTf:TextField = makeBoundedText(String(item.desc), 10, 0x647B91, secW - 75);



            descTf.x = 20;



            descTf.y = 20;



            row.addChild(descTf);



            // Нативный 3D чекбокс Maxis справа



            var isFlagOn:Boolean = (this.mContextFlagsState[item.key] !== false);



            var cb:SimsCheckbox = new SimsCheckbox(String(item.key), isFlagOn, function(k:String, st:Boolean):void {



                selfRef.onContextToggleClick(k, st);



            });



            cb.x = secW - 46;



            cb.y = Math.floor((rowH - 20) / 2);



            row.addChild(cb);



            this.mCheckboxesByKey[item.key] = cb;



            // Подсветка строки при наведении курсора



            row.addEventListener(MouseEvent.ROLL_OVER, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var rBg:Shape = targetRow.getChildAt(0) as Shape;



                    if (rBg != null)



                    {



                        rBg.graphics.clear();



                        rBg.graphics.beginFill(0x2E80C2, 0.08);



                        rBg.graphics.drawRoundRect(8, 1, secW - 16, rowH - 2, 6, 6);



                        rBg.graphics.endFill();



                    }



                }



            });



            row.addEventListener(MouseEvent.ROLL_OUT, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var rBg:Shape = targetRow.getChildAt(0) as Shape;



                    if (rBg != null)



                    {



                        rBg.graphics.clear();



                        rBg.graphics.beginFill(0xFFFFFF, 0.001);



                        rBg.graphics.drawRect(0, 0, secW, rowH);



                        rBg.graphics.endFill();



                    }



                }



            });



            // Клик по всей площади строки переключает чекбокс



            row.name = String(item.key);



            row.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var flagKey:String = targetRow.name;



                    var rowCb:SimsCheckbox = selfRef.mCheckboxesByKey[flagKey] as SimsCheckbox;



                    if (rowCb != null)



                    {



                        var curSt:Boolean = rowCb.getState();



                        rowCb.setState(!curSt);



                        selfRef.onContextToggleClick(flagKey, !curSt);



                    }



                }



            });



            container.addChild(row);



        }



    }



    public function getContextGroupsForCurrentMode():Array



    {



        var m:String = this.mCurrentContextMode;



        if (m == "thought")



        {



            return [



                {



                    "title": "ОСНОВНЫЕ ДАННЫЕ И ЛИЧНОСТЬ",



                    "items": [



                        {"key": "name", "title": "Имя персонажа", "desc": "Имя, фамилия и базовые паспортные данные сима."},



                        {"key": "age_gender", "title": "Возраст и пол", "desc": "Возрастная категория и биологический пол персонажа."},



                        {"key": "occult", "title": "Раса и оккультизм", "desc": "Человек, вампир, чародей, русалка, оборотень или пришелец."},



                        {"key": "traits", "title": "Черты характера", "desc": "Личность сима, архетипы WickedWhims и бонусные черты."},



                        {"key": "lore", "title": "Индивидуальный лор", "desc": "Личная биография и предыстория из карточки сима."},



                        {"key": "aspiration", "title": "Жизненная цель", "desc": "Выбранная жизненная цель и текущий этап развития."}



                    ]



                },



                {



                    "title": "СОСТОЯНИЕ И ПОТРЕБНОСТИ",



                    "items": [



                        {"key": "mood", "title": "Текущее настроение", "desc": "Доминирующая эмоция сима и причина (активный мудлет)."},



                        {"key": "needs", "title": "Потребности сима", "desc": "Критические нужды (голод, бодрость, гигиена, досуг и др.)."},



                        {"key": "activity", "title": "Текущее действие", "desc": "Анимация, занятие, поза и предмет в руках сима."},



                        {"key": "clothing", "title": "Одежда и наряд", "desc": "Категория наряда (повседневный, официальный, пижама и т.д.)."},



                        {"key": "nudity", "title": "Степень наготы", "desc": "Одет, топлес, в нижнем белье или полностью обнажен."},



                        {"key": "pregnancy", "title": "Беременность", "desc": "Факт беременности, триместр или отсутствие беременности."}



                    ]



                },



                {



                    "title": "ОКРУЖЕНИЕ И ОБСТАНОВКА",



                    "items": [



                        {"key": "world_time", "title": "Время в игре", "desc": "День недели, точный час и время суток (утро, день, вечер, ночь)."},



                        {"key": "weather", "title": "Время года и погода", "desc": "Текущий сезон, осадки, температура воздуха и облачность."},



                        {"key": "events", "title": "Праздники и традиции", "desc": "Календарные события, праздничные дни и актуальные традиции."},



                        {"key": "location", "title": "Локация персонажа", "desc": "Город, участок, внутри дома или на улице во дворе."},



                        {"key": "emergencies", "title": "ЧП и катастрофы", "desc": "Пожары, роды, удары током и смерть на участке."}



                    ]



                },



                {



                    "title": "ОТНОШЕНИЯ И ОКРУЖАЮЩИЕ",



                    "items": [



                        {"key": "nearby", "title": "Кто находится рядом", "desc": "Присутствие других симов в комнате или поблизости."},



                        {"key": "family", "title": "Семья и родственники", "desc": "Родители, дети, братья, сестры и романтические партнеры."},



                        {"key": "roommates", "title": "Соседи по дому", "desc": "Персонажи, проживающие на одном участке (не родственники)."},



                        {"key": "livein_staff", "title": "Домашняя прислуга", "desc": "Дворецкий, няня, горничная или садовник в доме."},



                        {"key": "pets", "title": "Домашние питомцы", "desc": "Собаки, кошки, лошади и мелкие животные семьи."},



                        {"key": "social", "title": "Друзья и знакомые", "desc": "Шкалы отношений с друзьями и городскими знакомыми."},



                        {"key": "incest", "title": "Табу и запретные связи", "desc": "Учитывать деликатные и запретные связи в семье."},



                        {"key": "recent_dialogs", "title": "Недавние диалоги", "desc": "Свежие разговоры и сообщения за последние 24 часа."},



                        {"key": "memory", "title": "Память о событиях", "desc": "Важные жизненные события, зафиксированные в памяти сима."}



                    ]



                },



                {



                    "title": "КАРЬЕРА, ФИНАНСЫ И СТАТУС",



                    "items": [



                        {"key": "career", "title": "Карьера и школа", "desc": "Профессия, успеваемость, график, выходные и домашка."},



                        {"key": "education", "title": "Высшее образование", "desc": "Университетский диплом, специальность и престиж."},



                        {"key": "funds", "title": "Бюджет семьи", "desc": "Количество симолеонов и уровень достатка домохозяйства."},



                        {"key": "fame", "title": "Слава и репутация", "desc": "Уровень известности (звезды) и общественная репутация."},



                        {"key": "clubs", "title": "Членство в клубах", "desc": "Клубы персонажа, его роль (лидер/член) и собрания."}



                    ]



                }



            ];



        }



        else if (m == "messenger")



        {



            return [



                {



                    "title": "ИСТОРИЯ И СВОДКА ПЕРЕПИСКИ",



                    "items": [



                        {"key": "summarize_personal", "title": "Сводка личных диалогов", "desc": "Сжимать старые сообщения в личной переписке."},



                        {"key": "summarize_group", "title": "Сводка групповых чатов", "desc": "Сжимать длинную историю в общих беседах."},



                        {"key": "summarize_direct", "title": "Сводка прямого общения", "desc": "Учитывать краткую историю недавних очных встреч."},



                        {"key": "chat_history", "title": "История переписки", "desc": "Контекст последних отправленных и полученных сообщений."},



                        {"key": "recent_dialogs", "title": "Недавние разговоры", "desc": "Память о недавних сообщениях за последние 24 часа."},



                        {"key": "chat_memory", "title": "Важные воспоминания", "desc": "Долгосрочные события и факты о симах в чате."}



                    ]



                },



                {



                    "title": "СОСТОЯНИЕ И ЛИЧНОСТЬ СОБЕСЕДНИКОВ",



                    "items": [



                        {"key": "chat_age_gender", "title": "Возраст и пол", "desc": "Возрастная категория и биологический пол авторов."},



                        {"key": "chat_occult", "title": "Раса и оккультизм", "desc": "Вампиры, чародеи, оборотни, пришельцы в переписке."},



                        {"key": "chat_traits", "title": "Черты характера", "desc": "Личностные качества и характер авторов сообщений."},



                        {"key": "chat_mood", "title": "Настроение собеседников", "desc": "Эмоциональное состояние участников при переписке."},



                        {"key": "chat_lore", "title": "Индивидуальный лор", "desc": "Личные биографии и предыстория участников переписки."},



                        {"key": "chat_aspiration", "title": "Жизненная цель", "desc": "Мечты и цели симов при обсуждении планов."},



                        {"key": "needs", "title": "Потребности авторов", "desc": "Учитывать жажду, голод или усталость при переписке."}



                    ]



                },



                {



                    "title": "ОБСТАНОВКА, ДЕЙСТВИЯ И СВЯЗИ",



                    "items": [



                        {"key": "chat_location", "title": "Локация собеседников", "desc": "Где находятся участники переписки в этот момент."},



                        {"key": "chat_activity", "title": "Текущее занятие", "desc": "Чем занимается сим в момент набора сообщения."},



                        {"key": "chat_clothing", "title": "Одежда и наряд", "desc": "Во что одет сим (пижама, костюм, купальник)."},



                        {"key": "chat_nearby", "title": "Кто рядом с симом", "desc": "Присутствие посторонних людей рядом с телефоном."},



                        {"key": "chat_relationship", "title": "Динамика отношений", "desc": "Дружеские и романтические шкалы между симами."},



                        {"key": "chat_family", "title": "Семья и родственники", "desc": "Родственные и семейные связи между собеседниками."},



                        {"key": "chat_roommates", "title": "Соседи по дому", "desc": "Симы, проживающие на одном участке."},



                        {"key": "chat_livein_staff", "title": "Домашняя прислуга", "desc": "Дворецкий, няня или горничная в доме автора."},



                        {"key": "chat_pets", "title": "Домашние животные", "desc": "Питомцы участников переписки."},



                        {"key": "chat_pregnancy", "title": "Беременность", "desc": "Беременность одного из собеседников."},



                        {"key": "chat_incest", "title": "Табу и запреты", "desc": "Границы общения и деликатные темы."},



                        {"key": "emergencies", "title": "ЧП и тревоги", "desc": "Пожар, схватки или критические ситуации на лоте."}



                    ]



                },



                {



                    "title": "КАРЬЕРА, ФИНАНСЫ И СТАТУС",



                    "items": [



                        {"key": "chat_career", "title": "Карьера и школа", "desc": "Профессия, успеваемость и рабочий статус авторов."},



                        {"key": "chat_funds", "title": "Бюджет и достаток", "desc": "Материальное положение семей авторов сообщений."},



                        {"key": "chat_fame", "title": "Слава и известность", "desc": "Звёздный статус симов в социальных сетях."},



                        {"key": "chat_clubs", "title": "Членство в клубах", "desc": "Клубные интересы и тусовки персонажей."}



                    ]



                }



            ];



        }



        else if (m == "direct")



        {



            return [



                {



                    "title": "ОБСТАНОВКА И ОКРУЖЕНИЕ",



                    "items": [



                        {"key": "dd_witnesses", "title": "Окружающие свидетели", "desc": "Кто находится рядом и слышит живой разговор."},



                        {"key": "dd_location", "title": "Локация и обстановка", "desc": "Комната, заведение, предметы рядом и тип участка."},



                        {"key": "dd_weather_time", "title": "Погода и время суток", "desc": "Время дня, температура, осадки и сезон года."},



                        {"key": "dd_events", "title": "События и праздники", "desc": "Активные городские праздники и текущие вечеринки."}



                    ]



                },



                {



                    "title": "УЧАСТНИКИ И ЛИЧНОСТИ",



                    "items": [



                        {"key": "dd_profiles", "title": "Профили персонажей", "desc": "Имена, возраст, пол и раса говорящих симов."},



                        {"key": "dd_traits", "title": "Черты характера", "desc": "Особенности характера и темперамент собеседников."},



                        {"key": "dd_mood", "title": "Текущие эмоции", "desc": "Эмоциональное состояние и настроение говорящих."},



                        {"key": "dd_lore", "title": "Индивидуальный лор", "desc": "Личные биографии и тайны участников разговора."},



                        {"key": "dd_activity", "title": "Текущее занятие", "desc": "Что симы держат в руках и чем заняты при беседе."},



                        {"key": "dd_clothing", "title": "Одежда и внешний вид", "desc": "Категория наряда и стиль собеседников."}



                    ]



                },



                {



                    "title": "ОТНОШЕНИЯ И ТЕМАТИКА",



                    "items": [



                        {"key": "dd_relationship", "title": "Отношения участников", "desc": "Уровень дружбы, романтики и динамика общения."},



                        {"key": "dd_family", "title": "Семейные узы", "desc": "Родственные связи и семейная иерархия между ними."},



                        {"key": "dd_memories", "title": "Совместные воспоминания", "desc": "Память о прошлых разговорах и важных моментах."},



                        {"key": "dd_business", "title": "Бизнес и карьера", "desc": "Работа, служебные темы и профессиональный статус."},



                        {"key": "dd_taboo", "title": "Личные границы", "desc": "Запретные темы, чувствительные вопросы и табу."}



                    ]



                }



            ];



        }



        else if (m == "intimate")



        {



            return [



                {



                    "title": "ФИЗИЧЕСКИЙ КОНТАКТ И АТМОСФЕРА",



                    "items": [



                        {"key": "id_pose", "title": "Поза и анимация", "desc": "Текущее положение и тип физического взаимодействия."},



                        {"key": "id_partners", "title": "Участники контакта", "desc": "Личности партнеров, их роли и динамика близости."},



                        {"key": "id_tone", "title": "Тон и атмосфера", "desc": "Нежность, доминирование, игривость или страсть."},



                        {"key": "id_attire", "title": "Состояние одежды", "desc": "Степень открытости и наряды партнеров."},



                        {"key": "id_traits", "title": "Черты характера", "desc": "Темперамент, раскованность или робость партнеров."}



                    ]



                },



                {



                    "title": "КОНФИДЕНЦИАЛЬНОСТЬ И ГРАНИЦЫ",



                    "items": [



                        {"key": "id_privacy", "title": "Уединенность места", "desc": "Закрытая комната, спальня или риск быть увиденным."},



                        {"key": "id_observers", "title": "Присутствие свидетелей", "desc": "Спят ли рядом симы или кто-то может зайти."},



                        {"key": "id_relationship", "title": "Глубина близости", "desc": "Страсть, любовь, мимолетная связь или брак."},



                        {"key": "id_taboo", "title": "Табу и границы", "desc": "Чего персонажи избегают или стесняются в сексе."},



                        {"key": "id_pregnancy", "title": "Риск беременности", "desc": "Учитывать возможность зачатия ребенка."},



                        {"key": "id_venue", "title": "Обстановка и мебель", "desc": "Кровать, душ, джакузи или общественное место."},



                        {"key": "id_memories", "title": "Интимная память", "desc": "Воспоминания о прошлом опыте близости партнеров."}



                    ]



                }



            ];



        }



        return [];



    }



    public function getContextItemsForCurrentMode():Array



    {



        var all:Array = [];



        var grps:Array = this.getContextGroupsForCurrentMode();



        for (var g:int = 0; g < grps.length; g++)



        {



            var gItems:Array = grps[g].items as Array;



            if (gItems != null)



            {



                for (var it:int = 0; it < gItems.length; it++)



                {



                    all.push(gItems[it]);



                }



            }



        }



        return all;



    }



    public function onContextToggleClick(flagKey:String, newState:Boolean):void



    {



        this.mContextFlagsState[flagKey] = newState;



        ExternalInterface.call("CallGameService", "PostServerCommand", {



            "command": "synapse.set_context_flag",



            "commandArgs": [this.mCurrentContextMode, flagKey, newState ? "1" : "0"]



        });



    }



    public function onBulkActionClick(action:String):void



    {



        var items:Array = this.getContextItemsForCurrentMode();



        for (var i:int = 0; i < items.length; i++)



        {



            var k:String = String(items[i].key);



            var newVal:Boolean = (action != "disable_all");



            this.mContextFlagsState[k] = newVal;



            if (this.mCheckboxesByKey[k] != null)



            {



                var cb:SimsCheckbox = this.mCheckboxesByKey[k] as SimsCheckbox;



                if (cb != null)



                {



                    cb.setState(newVal);



                }



            }



        }



        ExternalInterface.call("CallGameService", "PostServerCommand", {



            "command": "synapse.bulk_context_flags",



            "commandArgs": [this.mCurrentContextMode, action]



        });



    }



    public function buildLoreSection():void



    {



        this.mLoreContainer = new Sprite();



        this.mWorkspace.addChild(this.mLoreContainer);



        var secW:Number = WORKSPACE_W;



        var barH:Number = 28;



        // Секция 1: Выбор персонажа и Раса



        var sec1Y:Number = 0;



        var sec1BodyH:Number = 88;



        this.drawSectionContainerOn(this.mLoreContainer, sec1Y, secW, barH, sec1BodyH);



        var sec1Title:TextField = makeCenteredText("ВЫБОР ПЕРСОНАЖА ДЛЯ НАСТРОЙКИ ЛОРА", 13, 0xFFFFFF, secW);



        sec1Title.x = 0;



        sec1Title.y = sec1Y + 4;



        this.mLoreContainer.addChild(sec1Title);



        var pickBtn:SimsPillButton = new SimsPillButton("ВЫБРАТЬ ПЕРСОНАЖА", 180, 28, "pick_sim", "", this, false);



        pickBtn.x = 16;



        pickBtn.y = sec1Y + barH + 10;



        var selfRef:SettingsUI = this;



        pickBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.setModal(false);



            ExternalInterface.call("CallGameService", "PostServerCommand", {



                "command": "synapse.pick_lore_sim",



                "commandArgs": []



            });



        });



        this.mLoreContainer.addChild(pickBtn);



        var initSimLabel:String = (this.mCurrentSimName && this.mCurrentSimName != "") ? ("Персонаж: " + this.mCurrentSimName + " [ID: " + this.mCurrentSimId + "]") : "Персонаж: (загрузка...)";



        this.mSelectedSimLabel = makeText(initSimLabel, 13, COL_LABEL_DARK);



        this.mSelectedSimLabel.x = 206;



        this.mSelectedSimLabel.y = sec1Y + barH + 8;



        this.mLoreContainer.addChild(this.mSelectedSimLabel);



        this.mLoreStatusLabel = makeText("Индивидуальный лор не задан", 11, 0x667788);



        this.mLoreStatusLabel.x = 206;



        this.mLoreStatusLabel.y = sec1Y + barH + 28;



        this.mLoreContainer.addChild(this.mLoreStatusLabel);



        // Поле ввода расы персонажа



        var raceLabel:TextField = makeText("Раса / Оккульт персонажа:", 12, 0x1A4064);



        raceLabel.x = 16;



        raceLabel.y = sec1Y + barH + 54;



        this.mLoreContainer.addChild(raceLabel);



        var raceBorder:Shape = new Shape();



        raceBorder.graphics.beginFill(COL_BOX_BORDER, 1.0);



        raceBorder.graphics.drawRoundRect(195, sec1Y + barH + 51, 260, 24, 4, 4);



        raceBorder.graphics.endFill();



        this.mLoreContainer.addChild(raceBorder);



        var raceInner:Shape = new Shape();



        raceInner.graphics.beginFill(0xFFFFFF, 1.0);



        raceInner.graphics.drawRoundRect(196, sec1Y + barH + 52, 258, 22, 3, 3);



        raceInner.graphics.endFill();



        this.mLoreContainer.addChild(raceInner);



        this.mLoreRaceInput = new TextField();



        this.mLoreRaceInput.type = "input";



        this.mLoreRaceInput.embedFonts = true;



        this.mLoreRaceInput.selectable = true;



        this.mLoreRaceInput.mouseEnabled = true;



        this.mLoreRaceInput.multiline = false;



        this.mLoreRaceInput.x = 199;



        this.mLoreRaceInput.y = sec1Y + barH + 53;



        this.mLoreRaceInput.width = 252;



        this.mLoreRaceInput.height = 20;



        var raceTfFmt:TextFormat = new TextFormat("$TextFont", 12, COL_LABEL_DARK, false);



        this.mLoreRaceInput.defaultTextFormat = raceTfFmt;



        this.mLoreRaceInput.setTextFormat(raceTfFmt);



        this.mLoreRaceInput.maxChars = 60;



        this.mLoreRaceInput.addEventListener(FocusEvent.FOCUS_IN, function(e:FocusEvent):void {



            try {



                var cmFiR:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cmFiR.CallGameService("SetTextFieldInput", true);



            } catch(eFiR:Error) {}



        });



        this.mLoreRaceInput.addEventListener(FocusEvent.FOCUS_OUT, function(e:FocusEvent):void {



            try {



                var cmFoR:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cmFoR.CallGameService("SetTextFieldInput", false);



            } catch(eFoR:Error) {}



        });



        this.mLoreContainer.addChild(this.mLoreRaceInput);



        var raceHint:TextField = makeText("(Человек, Вампир, Эльф, Киборг...)", 11, 0x778899);



        raceHint.x = 464;



        raceHint.y = sec1Y + barH + 55;



        this.mLoreContainer.addChild(raceHint);



        // Секция 2: Биография и лор



        var sec2Y:Number = sec1Y + barH + sec1BodyH + 8;



        var sec2BodyH:Number = 312;



        this.drawSectionContainerOn(this.mLoreContainer, sec2Y, secW, barH, sec2BodyH);



        var sec2Title:TextField = makeCenteredText("БИОГРАФИЯ, ТАЙНЫ И ИНДИВИДУАЛЬНОСТЬ ДЛЯ ИИ", 13, 0xFFFFFF, secW);



        sec2Title.x = 0;



        sec2Title.y = sec2Y + 4;



        this.mLoreContainer.addChild(sec2Title);



        // Голубая подсказка Maxis



        var hintBg:Shape = new Shape();



        hintBg.graphics.beginFill(COL_ICE_BANNER, 1.0);



        hintBg.graphics.drawRoundRect(10, sec2Y + barH + 8, secW - 20, 40, 6, 6);



        hintBg.graphics.endFill();



        this.mLoreContainer.addChild(hintBg);



        var hintTf:TextField = makeText("Опишите предысторию, секреты, цели или манеру речи персонажа.\nИИ будет строго опираться на этот контекст при формировании мыслей и решений.", 11, 0x244257);



        hintTf.x = 20;



        hintTf.y = sec2Y + barH + 11;



        this.mLoreContainer.addChild(hintTf);



        // Текстовое поле ввода лора



        var inpY:Number = sec2Y + barH + 48;



        var inpH:Number = 212;



        var inpW:Number = secW - 24;



        var inputBorder:Shape = new Shape();



        inputBorder.graphics.beginFill(COL_BOX_BORDER, 1.0);



        inputBorder.graphics.drawRoundRect(12, inpY, inpW, inpH, 6, 6);



        inputBorder.graphics.endFill();



        this.mLoreContainer.addChild(inputBorder);



        var inputInner:Shape = new Shape();



        inputInner.graphics.beginFill(0xFFFFFF, 1.0);



        inputInner.graphics.drawRoundRect(13, inpY + 1, inpW - 2, inpH - 2, 5, 5);



        inputInner.graphics.endFill();



        this.mLoreContainer.addChild(inputInner);



        this.mLoreInput = new TextField();



        this.mLoreInput.type = "input";



        this.mLoreInput.embedFonts = true;



        this.mLoreInput.selectable = true;



        this.mLoreInput.mouseEnabled = true;



        this.mLoreInput.multiline = true;



        this.mLoreInput.wordWrap = true;



        this.mLoreInput.x = 18;



        this.mLoreInput.y = inpY + 6;



        this.mLoreInput.width = inpW - 12;



        this.mLoreInput.height = inpH - 12;



        var tfFmt:TextFormat = new TextFormat("$TextFont", 13, COL_LABEL_DARK, false);



        tfFmt.leading = 3;



        this.mLoreInput.defaultTextFormat = tfFmt;



        this.mLoreInput.setTextFormat(tfFmt);



        this.mLoreInput.maxChars = 2000;



        this.mLoreInput.addEventListener(FocusEvent.FOCUS_IN, function(e:FocusEvent):void {



            try {



                var cmFi:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cmFi.CallGameService("SetTextFieldInput", true);



            } catch(eFi:Error) {}



        });



        this.mLoreInput.addEventListener(FocusEvent.FOCUS_OUT, function(e:FocusEvent):void {



            try {



                var cmFo:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cmFo.CallGameService("SetTextFieldInput", false);



            } catch(eFo:Error) {}



        });



        this.mLoreInput.addEventListener(Event.CHANGE, function(e:Event):void {



            selfRef.mLoreInput.defaultTextFormat = tfFmt;



            selfRef.updateLoreCounter();



            if (selfRef.mLoreSavedBadge) {



                selfRef.mLoreSavedBadge.visible = false;



            }



        });



        this.mLoreContainer.addChild(this.mLoreInput);



        // Нижняя панель действий



        this.mLoreCounter = makeText("Символов: 0 / 2000", 12, 0x8899A6);



        this.mLoreCounter.x = 16;



        this.mLoreCounter.y = sec2Y + barH + 268;



        this.mLoreContainer.addChild(this.mLoreCounter);



        this.mLoreSavedBadge = makeText("Сохранено!", 12, 0x1E824C);



        this.mLoreSavedBadge.x = 170;



        this.mLoreSavedBadge.y = sec2Y + barH + 268;



        this.mLoreSavedBadge.visible = false;



        this.mLoreContainer.addChild(this.mLoreSavedBadge);



        var saveBtn:SimsPillButton = new SimsPillButton("СОХРАНИТЬ", 130, 32, "save_lore", "", this, false);



        saveBtn.x = secW - 16 - 130 - 10 - 130;



        saveBtn.y = sec2Y + barH + 262;



        saveBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            var simId:String = selfRef.mCurrentSimId;



            var txt:String = selfRef.mLoreInput ? selfRef.mLoreInput.text : "";



            var raceTxt:String = selfRef.mLoreRaceInput ? selfRef.mLoreRaceInput.text : "";



            ExternalInterface.call("CallGameService", "PostServerCommand", {



                "command": "synapse.save_lore",



                "commandArgs": [simId, selfRef.encodeSafeStr(txt), selfRef.encodeSafeStr(raceTxt)]



            });



        });



        this.mLoreContainer.addChild(saveBtn);



        var clearBtn:SimsPillButton = new SimsPillButton("ОЧИСТИТЬ ЛОР", 130, 32, "clear_lore", "", this, false);



        clearBtn.x = secW - 16 - 130;



        clearBtn.y = sec2Y + barH + 262;



        clearBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            var simId:String = selfRef.mCurrentSimId;



            ExternalInterface.call("CallGameService", "PostServerCommand", {



                "command": "synapse.clear_lore",



                "commandArgs": [simId]



            });



        });



        this.mLoreContainer.addChild(clearBtn);



        if (this.mCurrentSimName && this.mCurrentSimName.length > 0)



        {



            this.mSelectedSimLabel.text = "Персонаж: " + this.mCurrentSimName + " [ID: " + this.mCurrentSimId + "]";



            this.mLoreInput.text = this.mCurrentLoreText;



            if (this.mLoreRaceInput != null) {



                this.mLoreRaceInput.text = this.mCurrentRaceText;



            }



            this.updateLoreCounter();



        }



        this.mLoreContainer.visible = true;



    }



    // =========================================================================



    // ВСПЛЫВАЮЩИЙ ЭКРАН 3: АВТОНОМИЯ МЫСЛЕЙ (100% MAXIS UI)



    // =========================================================================



    public function buildAutonomySection():void



    {



        this.mAutonomyContainer = new Sprite();



        this.mAutonomyContainer.visible = false;



        this.mWorkspace.addChild(this.mAutonomyContainer);



        var secW:Number = WORKSPACE_W;



        var barH:Number = 28;



        var selfRef:SettingsUI = this;



        // =========================================================================



        // СЕКЦИЯ 1: РЕЖИМ АВТОНОМИИ (ВКЛ / ВЫКЛ)



        // =========================================================================



        var sec1Y:Number = 0;



        var sec1BodyH:Number = 88;



        this.drawSectionContainerOn(this.mAutonomyContainer, sec1Y, secW, barH, sec1BodyH);



        var sec1Title:TextField = makeCenteredText("АВТОНОМНАЯ ГЕНЕРАЦИЯ МЫСЛЕЙ (ВКЛ / ВЫКЛ)", 13, 0xFFFFFF, secW);



        sec1Title.x = 0;



        sec1Title.y = sec1Y + 4;



        this.mAutonomyContainer.addChild(sec1Title);



        // Ледяной баннер подсказки Maxis



        var hintBg:Shape = new Shape();



        hintBg.graphics.beginFill(COL_ICE_BANNER, 1.0);



        hintBg.graphics.drawRoundRect(10, sec1Y + barH + 6, secW - 20, 30, 6, 6);



        hintBg.graphics.endFill();



        this.mAutonomyContainer.addChild(hintBg);



        var hintTf:TextField = makeText("Персонажи периодически генерируют мысли в облачках над головой в фоне во время игры.", 11, 0x244257);



        hintTf.x = 20;



        hintTf.y = sec1Y + barH + 12;



        this.mAutonomyContainer.addChild(hintTf);



        // Интерактивная строка с чекбоксом Maxis



        var rowH:Number = 38;



        var rowY:Number = sec1Y + barH + 42;



        var rowSprite:Sprite = new Sprite();



        rowSprite.x = 10;



        rowSprite.y = rowY;



        rowSprite.buttonMode = true;



        rowSprite.useHandCursor = true;



        var rowBg:Shape = new Shape();



        rowBg.graphics.beginFill(0xFFFFFF, 0.001);



        rowBg.graphics.drawRect(0, 0, secW - 20, rowH);



        rowBg.graphics.endFill();



        rowSprite.addChild(rowBg);



        var titleTf:TextField = makeText("Включить фоновую автономию мыслей", 12, 0x19456B);



        titleTf.x = 10;



        titleTf.y = 3;



        titleTf.mouseEnabled = false;



        rowSprite.addChild(titleTf);



        var descTf:TextField = makeText("Автоматическая генерация мыслей по таймеру для активного персонажа", 10, 0x647B91);



        descTf.x = 10;



        descTf.y = 19;



        descTf.mouseEnabled = false;



        rowSprite.addChild(descTf);



        this.mAutonomyCheckbox = new SimsCheckbox("autonomy_enabled", this.mAutonomyEnabled, function(k:String, st:Boolean):void {



            selfRef.onAutonomyToggleClick(st);



        });



        this.mAutonomyCheckbox.x = secW - 20 - 46;



        this.mAutonomyCheckbox.y = Math.floor((rowH - 20) / 2);



        rowSprite.addChild(this.mAutonomyCheckbox);



        rowSprite.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            var curSt:Boolean = selfRef.mAutonomyCheckbox.getState();



            selfRef.mAutonomyCheckbox.setState(!curSt);



            selfRef.onAutonomyToggleClick(!curSt);



        });



        this.mAutonomyContainer.addChild(rowSprite);



        // =========================================================================



        // СЕКЦИЯ 2: НАСТРОЙКА ИНТЕРВАЛА ВРЕМЕНИ (ПРЕСЕТЫ + СВОЁ ВРЕМЯ)



        // =========================================================================



        var sec2Y:Number = sec1Y + barH + sec1BodyH + 10;



        var sec2BodyH:Number = 220;



        this.drawSectionContainerOn(this.mAutonomyContainer, sec2Y, secW, barH, sec2BodyH);



        var sec2Title:TextField = makeCenteredText("ПЕРИОДИЧНОСТЬ И ИНТЕРВАЛ ВРЕМЕНИ", 13, 0xFFFFFF, secW);



        sec2Title.x = 0;



        sec2Title.y = sec2Y + 4;



        this.mAutonomyContainer.addChild(sec2Title);



        // Текущий статус интервала



        var curIntervalLabel:TextField = makeText("ТЕКУЩИЙ ИНТЕРВАЛ:", 11, 0x5A738E);



        curIntervalLabel.x = 16;



        curIntervalLabel.y = sec2Y + barH + 10;



        this.mAutonomyContainer.addChild(curIntervalLabel);



        this.mAutonomyStatusTf = makeText("", 13, 0x19456B);



        this.mAutonomyStatusTf.x = 160;



        this.mAutonomyStatusTf.y = sec2Y + barH + 9;



        this.mAutonomyContainer.addChild(this.mAutonomyStatusTf);



        // Пресеты времени



        var presetsLabel:TextField = makeText("Быстрый выбор интервала:", 11, 0x5A738E);



        presetsLabel.x = 16;



        presetsLabel.y = sec2Y + barH + 34;



        this.mAutonomyContainer.addChild(presetsLabel);



        var presets:Array = [



            {"label": "1 ЧАС (60м)", "mins": 60},



            {"label": "4 ЧАСА (240м)", "mins": 240},



            {"label": "8 ЧАСОВ (480м)", "mins": 480},



            {"label": "16 ЧАСОВ", "mins": 960},



            {"label": "24 ЧАСА", "mins": 1440}



        ];



        var btnW:Number = 106;



        var btnH:Number = 26;



        var btnStartX:Number = 16;



        var btnY:Number = sec2Y + barH + 54;



        this.mAutonomyPresetBtns = [];



        for (var pIdx:int = 0; pIdx < presets.length; pIdx++)



        {



            var pObj:Object = presets[pIdx];



            var pBtn:SimsPillButton = new SimsPillButton(



                String(pObj.label),



                btnW,



                btnH,



                "",



                "",



                this,



                false,



                11



            );



            pBtn.x = btnStartX + pIdx * (btnW + 8);



            pBtn.y = btnY;



            pBtn.name = String(pObj.mins);



            pBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



                var targetBtn:Sprite = e.currentTarget as Sprite;



                if (targetBtn != null)



                {



                    var mVal:int = parseInt(targetBtn.name);



                    selfRef.applyAutonomyInterval(mVal);



                }



            });



            this.mAutonomyContainer.addChild(pBtn);



            this.mAutonomyPresetBtns.push(pBtn);



        }



        // Разделительная черта



        var sep1:Shape = new Shape();



        sep1.graphics.lineStyle(1, 0xCBD6E2, 0.5);



        sep1.graphics.moveTo(16, sec2Y + barH + 92);



        sep1.graphics.lineTo(secW - 16, sec2Y + barH + 92);



        this.mAutonomyContainer.addChild(sep1);



        // Блок произвольного времени (ЛЮБОЕ ВРЕМЯ)



        var customTimeLabel:TextField = makeText("Указать своё точное время (любое количество сим-минут):", 12, 0x19456B);



        customTimeLabel.x = 16;



        customTimeLabel.y = sec2Y + barH + 104;



        this.mAutonomyContainer.addChild(customTimeLabel);



        // Инпут для ввода минут



        var inpX:Number = 16;



        var inpY:Number = sec2Y + barH + 128;



        var inpW:Number = 110;



        var inpH:Number = 30;



        var inpBorder:Shape = new Shape();



        inpBorder.graphics.beginFill(COL_BOX_BORDER, 1.0);



        inpBorder.graphics.drawRoundRect(inpX, inpY, inpW, inpH, 6, 6);



        inpBorder.graphics.endFill();



        this.mAutonomyContainer.addChild(inpBorder);



        var inpInner:Shape = new Shape();



        inpInner.graphics.beginFill(0xFFFFFF, 1.0);



        inpInner.graphics.drawRoundRect(inpX + 1, inpY + 1, inpW - 2, inpH - 2, 5, 5);



        inpInner.graphics.endFill();



        this.mAutonomyContainer.addChild(inpInner);



        this.mAutonomyCustomInput = new TextField();



        this.mAutonomyCustomInput.type = "input";



        this.mAutonomyCustomInput.embedFonts = true;



        this.mAutonomyCustomInput.selectable = true;



        this.mAutonomyCustomInput.mouseEnabled = true;



        this.mAutonomyCustomInput.multiline = false;



        this.mAutonomyCustomInput.restrict = "0-9";



        this.mAutonomyCustomInput.maxChars = 5;



        this.mAutonomyCustomInput.x = inpX + 6;



        this.mAutonomyCustomInput.y = inpY + 5;



        this.mAutonomyCustomInput.width = inpW - 12;



        this.mAutonomyCustomInput.height = inpH - 10;



        var inFmt:TextFormat = new TextFormat("$TextFont", 14, 0x19456B, true);



        this.mAutonomyCustomInput.defaultTextFormat = inFmt;



        this.mAutonomyCustomInput.setTextFormat(inFmt);



        this.mAutonomyCustomInput.text = String(this.mAutonomyInterval);



        this.mAutonomyCustomInput.addEventListener(FocusEvent.FOCUS_IN, function(e:FocusEvent):void {



            try {



                var cmFi:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cmFi.CallGameService("SetTextFieldInput", true);



            } catch(eFi:Error) {}



        });



        this.mAutonomyCustomInput.addEventListener(FocusEvent.FOCUS_OUT, function(e:FocusEvent):void {



            try {



                var cmFo:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cmFo.CallGameService("SetTextFieldInput", false);



            } catch(eFo:Error) {}



        });



        this.mAutonomyContainer.addChild(this.mAutonomyCustomInput);



        var minsHintTf:TextField = makeText("сим-минут  (например: 30 = полчаса, 90 = 1.5 ч., 180 = 3 ч., 720 = 12 ч.)", 11, 0x647B91);



        minsHintTf.x = inpX + inpW + 12;



        minsHintTf.y = inpY + 6;



        this.mAutonomyContainer.addChild(minsHintTf);



        // Кнопка Применить своё время



        var applyBtn:SimsPillButton = new SimsPillButton("ПРИМЕНИТЬ", 140, 30, "", "", this, false, 12);



        applyBtn.x = inpX;



        applyBtn.y = inpY + inpH + 12;



        applyBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            var rawText:String = selfRef.mAutonomyCustomInput ? selfRef.mAutonomyCustomInput.text : "";



            var parsedVal:int = parseInt(rawText);



            if (parsedVal > 0)



            {



                selfRef.applyAutonomyInterval(parsedVal);



                if (selfRef.mAutonomySavedBadge != null)



                {



                    selfRef.mAutonomySavedBadge.visible = true;



                    setTimeout(function():void {



                        if (selfRef.mAutonomySavedBadge != null) selfRef.mAutonomySavedBadge.visible = false;



                    }, 2500);



                }



            }



        });



        this.mAutonomyContainer.addChild(applyBtn);



        this.mAutonomySavedBadge = makeText("Время сохранено!", 12, 0x1E824C);



        this.mAutonomySavedBadge.x = inpX + 152;



        this.mAutonomySavedBadge.y = inpY + inpH + 18;



        this.mAutonomySavedBadge.visible = false;



        this.mAutonomyContainer.addChild(this.mAutonomySavedBadge);



        this.refreshAutonomyUI();



    }



    public function onAutonomyToggleClick(enabled:Boolean):void



    {



        this.mAutonomyEnabled = enabled;



        ExternalInterface.call("CallGameService", "PostServerCommand", {



            "command": "synapse.set_autonomy_enabled",



            "commandArgs": [enabled ? "1" : "0"]



        });



        this.refreshAutonomyUI();



    }



    public function applyAutonomyInterval(mins:int):void



    {



        if (mins <= 0) return;



        this.mAutonomyInterval = mins;



        ExternalInterface.call("CallGameService", "PostServerCommand", {



            "command": "synapse.set_autonomy_interval",



            "commandArgs": [String(mins)]



        });



        if (this.mAutonomyCustomInput != null)



        {



            this.mAutonomyCustomInput.text = String(mins);



        }



        this.refreshAutonomyUI();



    }



    public function refreshAutonomyUI():void



    {



        if (this.mAutonomyCheckbox != null)



        {



            this.mAutonomyCheckbox.setState(this.mAutonomyEnabled);



        }



        if (this.mAutonomyStatusTf != null)



        {



            var str:String = "";



            var mins:int = this.mAutonomyInterval;



            if (mins >= 60)



            {



                var h:int = Math.floor(mins / 60);



                var remM:int = mins % 60;



                if (remM > 0)



                {



                    str = "Каждые " + h + " ч. " + remM + " мин. (" + mins + " сим-минут)";



                }



                else



                {



                    if (h == 24) str = "Каждые 24 ч. (Раз в игровые сутки)";



                    else if (h == 4) str = "Каждые 4 ч. (240 сим-минут) [Рекомендуется]";



                    else str = "Каждые " + h + " ч. (" + mins + " сим-минут)";



                }



            }



            else



            {



                str = "Каждые " + mins + " сим-минут";



            }



            this.mAutonomyStatusTf.text = str;



        }



        if (this.mAutonomyPresetBtns != null)



        {



            for (var i:int = 0; i < this.mAutonomyPresetBtns.length; i++)



            {



                var pBtn:SimsPillButton = this.mAutonomyPresetBtns[i] as SimsPillButton;



                if (pBtn != null)



                {



                    var pVal:int = parseInt(pBtn.name);



                    pBtn.setSelected(pVal == this.mAutonomyInterval);



                }



            }



        }



    }



    // =========================================================================



    // GENEALOGY & KINSHIP SETTINGS SECTION & LOGIC



    // =========================================================================



    public function buildGenealogySection():void



    {



        this.mGenealogyContainer = new Sprite();



        this.mGenealogyContainer.visible = false;



        this.mWorkspace.addChild(this.mGenealogyContainer);



        var secW:Number = WORKSPACE_W;



        var barH:Number = 28;



        var secY:Number = 0;



        var secBodyH:Number = 430;



        var selfRef:SettingsUI = this;



        // Внешняя секция



        this.drawSectionContainerOn(this.mGenealogyContainer, secY, secW, barH, secBodyH);



        var secTitle:TextField = makeCenteredText("ФИЛЬТРЫ РОДСТВА И СЕМЕЙНЫХ СВЯЗЕЙ", 13, 0xFFFFFF, secW);



        secTitle.x = 0;



        secTitle.y = secY + 4;



        this.mGenealogyContainer.addChild(secTitle);



        // Ледяной информационный баннер подсказки



        var hintBg:Shape = new Shape();



        var hMat:Matrix = new Matrix();



        hMat.createGradientBox(secW - 24, 26, Math.PI / 2, 0, 0);



        hintBg.graphics.beginGradientFill(



            GradientType.LINEAR,



            [0xECF3FA, 0xDFEAF4],



            [1.0, 1.0],



            [0, 255],



            hMat



        );



        hintBg.graphics.lineStyle(1, 0xB8CBDC, 0.8, true);



        hintBg.graphics.drawRoundRect(12, secY + barH + 6, secW - 24, 26, 6, 6);



        hintBg.graphics.endFill();



        this.mGenealogyContainer.addChild(hintBg);



        var hintTf:TextField = makeText("Настройка категорий родственников, глубины поколений и бывших партнёров для ИИ.", 11, 0x1E466B);



        hintTf.x = 22;



        hintTf.y = secY + barH + 11;



        this.mGenealogyContainer.addChild(hintTf);



        // Скролл-контейнер MaxisScrollView



        var scrollW:Number = secW - 24;



        var scrollH:Number = secBodyH - 80;



        this.mGenealogyScrollView = new MaxisScrollView(scrollW, scrollH);



        this.mGenealogyScrollView.x = 12;



        this.mGenealogyScrollView.y = secY + barH + 74;



        this.mGenealogyContainer.addChild(this.mGenealogyScrollView);



        // Верхняя панель действий (кнопки ВКЛ ВСЕ / ВЫКЛ ВСЕ / ПО УМОЛЧАНИЮ)



        var topControlsBar:Sprite = new Sprite();



        var topBarBg:Shape = new Shape();



        topBarBg.graphics.beginFill(0xFFFFFF, 1.0);



        topBarBg.graphics.drawRect(1, secY + barH + 36, secW - 2, 36);



        topBarBg.graphics.endFill();



        topControlsBar.addChild(topBarBg);



        var bulkAllOnBtn:SimsPillButton = new SimsPillButton("ВКЛЮЧИТЬ ВСЕ", 132, 26, "gene_all_on", "", this, false, 11);



        bulkAllOnBtn.x = 12;



        bulkAllOnBtn.y = secY + barH + 40;



        bulkAllOnBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.onBulkGenealogyActionClick("enable_all");



        });



        topControlsBar.addChild(bulkAllOnBtn);



        var bulkAllOffBtn:SimsPillButton = new SimsPillButton("ВЫКЛЮЧИТЬ ВСЕ", 136, 26, "gene_all_off", "", this, false, 11);



        bulkAllOffBtn.x = 152;



        bulkAllOffBtn.y = secY + barH + 40;



        bulkAllOffBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.onBulkGenealogyActionClick("disable_all");



        });



        topControlsBar.addChild(bulkAllOffBtn);



        var bulkResetBtn:SimsPillButton = new SimsPillButton("ПО УМОЛЧАНИЮ", 132, 26, "gene_reset", "", this, false, 11);



        bulkResetBtn.x = 296;



        bulkResetBtn.y = secY + barH + 40;



        bulkResetBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.onBulkGenealogyActionClick("reset_defaults");



        });



        topControlsBar.addChild(bulkResetBtn);



        this.mGenealogyContainer.addChild(topControlsBar);



        // Нижняя защитная белая плашка



        var bottomCap:Shape = new Shape();



        bottomCap.graphics.beginFill(0xFFFFFF, 1.0);



        bottomCap.graphics.drawRoundRect(1, secY + barH + secBodyH - 8, secW - 2, 7, 4, 4);



        bottomCap.graphics.endFill();



        this.mGenealogyContainer.addChild(bottomCap);



    }



    public function reflowGenealogyAccordions():void



    {



        var currY:Number = 0;



        var gap:Number = 6;



        for (var i:int = 0; i < this.mGenealogyAccordionSections.length; i++)



        {



            var sec:MaxisAccordionSection = this.mGenealogyAccordionSections[i] as MaxisAccordionSection;



            if (sec != null)



            {



                sec.y = currY;



                currY += sec.getTotalHeight() + gap;



            }



        }



        if (this.mGenealogyScrollView != null)



        {



            this.mGenealogyScrollView.updateLayout(currY);



        }



    }



    public function getGenealogyGroups():Array



    {



        return [



            {



                "title": "1. БЫВШИЕ ПАРТНЁРЫ И СОЮЗЫ",



                "items": [



                    {



                        "key": "ex_partners",



                        "title": "Бывшие партнеры и прошлые союзы",



                        "desc": "Бывшие мужья/жены (развод), помолвки, пары (расставание), статус вдовства"



                    },



                    {



                        "key": "ex_in_laws",



                        "title": "Родственники бывших партнеров",



                        "desc": "Родители, братья/сестры и родня бывших супругов и партнеров (с указанием имени)"



                    }



                ]



            },



            {



                "title": "2. ПРЯМАЯ И СВОДНАЯ СЕМЬЯ",



                "items": [



                    {



                        "key": "spouses",



                        "title": "Супруги и постоянная пара",



                        "desc": "Муж, жена, жених, невеста, парень, девушка"



                    },



                    {



                        "key": "parents",



                        "title": "Родители",



                        "desc": "Отец, мать, отчим, мачеха, приёмные и тайные родители"



                    },



                    {



                        "key": "children",



                        "title": "Дети",



                        "desc": "Сыновья, дочери, пасынки, падчерицы, приёмные дети и подопечные"



                    },



                    {



                        "key": "siblings",



                        "title": "Братья и сестры",



                        "desc": "Родные, сводные, единокровные (по отцу) и единоутробные (по матери)"



                    }



                ]



            },



            {



                "title": "3. ГЛУБИНА ПРЕДКОВ И ПОТОМКОВ",



                "is_depth_section": true,



                "items": [



                    {



                        "key": "grandparents",



                        "title": "Дедушки и бабушки",



                        "desc": "2-е поколение предков (родители отца и матери)"



                    },



                    {



                        "key": "grandchildren",



                        "title": "Внуки и внучки",



                        "desc": "2-е поколение потомков (дети сыновей и дочерей)"



                    },



                    {



                        "key": "ancestors_extended",



                        "title": "Дальние предки 3+ поколений",



                        "desc": "Прадедушки, прабабушки, прапрадедушки и старшие поколения предков"



                    },



                    {



                        "key": "descendants_extended",



                        "title": "Дальние потомки 3+ поколений",



                        "desc": "Правнуки, правнучки, праправнуки и младшие поколения потомков"



                    }



                ]



            },



            {



                "title": "4. ДАЛЬНЯЯ РОДНЯ И СВОЙСТВЕННИКИ",



                "items": [



                    {



                        "key": "extended",



                        "title": "Дяди, тети и кузены",



                        "desc": "Братья и сестры родителей, двоюродные братья и сестры"



                    },



                    {



                        "key": "sibling_family",



                        "title": "Семья братьев и сестер",



                        "desc": "Племянники, племянницы, их супруги и внучатые племянники"



                    },



                    {



                        "key": "spouse_in_laws",



                        "title": "Родня со стороны супруга",



                        "desc": "Тесть, тёща, свёкор, свекровь, деверь, золовка, свояченица, свояк"



                    },



                    {



                        "key": "child_spouses",



                        "title": "Семья детей (Невестка / Зять)",



                        "desc": "Супруги сыновей и дочерей (невестка, сноха, зять)"



                    },



                    {



                        "key": "child_in_laws",



                        "title": "Родственники невестки и зятя",



                        "desc": "Сваты и родственники супругов ваших детей"



                    }



                ]



            },



            {



                "title": "5. ОСОБЫЕ ФИЛЬТРЫ",



                "items": [



                    {



                        "key": "deceased",



                        "title": "Покойные (умершие) родственники",



                        "desc": "Учитывать ли умерших предков и родственников в семейном древе"



                    }



                ]



            }



        ];



    }



    public function rebuildGenealogyItems():void



    {



        if (!this.mGenealogyScrollView) return;



        var prevScroll:Number = this.mGenealogyScrollView.getScrollY();



        var scrollContent:Sprite = this.mGenealogyScrollView.getContent();



        while (scrollContent.numChildren > 0)



        {



            scrollContent.removeChildAt(0);



        }



        this.mGenealogyAccordionSections = [];



        this.mGenealogyCheckboxesByKey = {};



        this.mGenealogyDepthBtns = [];



        var groups:Array = this.getGenealogyGroups();



        var secW:Number = this.mGenealogyScrollView.getViewportWidth();



        var selfRef:SettingsUI = this;



        for (var gIdx:int = 0; gIdx < groups.length; gIdx++)



        {



            var grp:Object = groups[gIdx];



            var secTitle:String = String(grp.title);



            var secKey:String = "gene_" + secTitle;



            var isInitiallyExpanded:Boolean = (this.mGenealogyExpandedSections[secKey] !== undefined) ?



                Boolean(this.mGenealogyExpandedSections[secKey]) : true;



            var accSec:MaxisAccordionSection = new MaxisAccordionSection(



                secTitle,



                secW,



                28,



                isInitiallyExpanded,



                function(tSec:MaxisAccordionSection):void {



                    var k:String = "gene_" + tSec.title;



                    selfRef.mGenealogyExpandedSections[k] = tSec.isExpanded;



                    selfRef.reflowGenealogyAccordions();



                }



            );



            // Специфический селектор глубины для секции 3



            var startRowY:Number = 0;



            if (grp.is_depth_section)



            {



                var depthRowH:Number = 42;



                var depthRow:Sprite = new Sprite();



                depthRow.y = 0;



                var dRowBg:Shape = new Shape();



                dRowBg.graphics.beginFill(COL_ICE_BANNER, 0.7);



                dRowBg.graphics.drawRoundRect(10, 2, secW - 20, depthRowH - 4, 6, 6);



                dRowBg.graphics.endFill();



                depthRow.addChild(dRowBg);



                var dLabel:TextField = makeText("Макс. глубина древа:", 11, 0x19456B);



                dLabel.x = 18;



                dLabel.y = 11;



                depthRow.addChild(dLabel);



                var depths:Array = [



                    {"label": "2 пок.", "depth": 2, "w": 50},



                    {"label": "3 пок.", "depth": 3, "w": 50},



                    {"label": "4 пок.", "depth": 4, "w": 50},



                    {"label": "5 пок.", "depth": 5, "w": 50},



                    {"label": "10 пок.", "depth": 10, "w": 56},



                    {"label": "Без ограничений", "depth": 0, "w": 120}



                ];



                var dBtnH:Number = 24;



                var currentX:Number = 160;



                for (var dIdx:int = 0; dIdx < depths.length; dIdx++)



                {



                    var dObj:Object = depths[dIdx];



                    var btnW:Number = Number(dObj.w);



                    var dBtn:SimsPillButton = new SimsPillButton(



                        String(dObj.label),



                        btnW,



                        dBtnH,



                        "",



                        "",



                        this,



                        false,



                        11



                    );



                    dBtn.x = currentX;



                    dBtn.y = 9;



                    dBtn.name = String(dObj.depth);



                    dBtn.setSelected(dObj.depth == this.mGenealogyDepth);



                    dBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



                        var targetBtn:Sprite = e.currentTarget as Sprite;



                        if (targetBtn != null)



                        {



                            var targetDepth:int = parseInt(targetBtn.name);



                            selfRef.applyGenealogyDepth(targetDepth);



                        }



                    });



                    depthRow.addChild(dBtn);



                    this.mGenealogyDepthBtns.push(dBtn);



                    currentX += btnW + 5;



                }



                accSec.content.addChild(depthRow);



                startRowY = depthRowH + 4;



            }



            var grpItems:Array = grp.items as Array;



            if (grpItems != null)



            {



                this.populateGenealogySectionItems(accSec.content, grpItems, secW, startRowY);



            }



            scrollContent.addChild(accSec);



            this.mGenealogyAccordionSections.push(accSec);



        }



        this.mGenealogyScrollView.setOwnerSections(this.mGenealogyAccordionSections);



        this.reflowGenealogyAccordions();



        if (prevScroll > 0)



        {



            this.mGenealogyScrollView.scrollTo(prevScroll);



        }



        else



        {



            this.mGenealogyScrollView.resetScroll();



        }



    }



    private function populateGenealogySectionItems(container:Sprite, items:Array, secW:Number, startY:Number = 0):void



    {



        var rowH:Number = 40;



        var selfRef:SettingsUI = this;



        for (var i:int = 0; i < items.length; i++)



        {



            var item:Object = items[i];



            var row:Sprite = new Sprite();



            row.y = startY + i * rowH;



            row.buttonMode = true;



            row.useHandCursor = true;



            row.mouseChildren = true;



            var rowBg:Shape = new Shape();



            rowBg.graphics.beginFill(0xFFFFFF, 0.001);



            rowBg.graphics.drawRect(0, 0, secW, rowH);



            rowBg.graphics.endFill();



            row.addChild(rowBg);



            var sep:Shape = new Shape();



            sep.graphics.lineStyle(1, 0xCBD6E2, 0.40);



            sep.graphics.moveTo(16, rowH - 1);



            sep.graphics.lineTo(secW - 16, rowH - 1);



            row.addChild(sep);



            var titleTf:TextField = makeBoundedText(String(item.title), 12, 0x19456B, secW - 75);



            titleTf.x = 20;



            titleTf.y = 4;



            row.addChild(titleTf);



            var descTf:TextField = makeBoundedText(String(item.desc), 10, 0x647B91, secW - 75);



            descTf.x = 20;



            descTf.y = 20;



            row.addChild(descTf);



            var isFlagOn:Boolean = (this.mGenealogyFlagsState[item.key] !== false);



            var cb:SimsCheckbox = new SimsCheckbox(String(item.key), isFlagOn, function(k:String, st:Boolean):void {



                selfRef.onGenealogyToggleClick(k, st);



            });



            cb.x = secW - 46;



            cb.y = Math.floor((rowH - 20) / 2);



            row.addChild(cb);



            this.mGenealogyCheckboxesByKey[item.key] = cb;



            row.addEventListener(MouseEvent.ROLL_OVER, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var rBg:Shape = targetRow.getChildAt(0) as Shape;



                    if (rBg != null)



                    {



                        rBg.graphics.clear();



                        rBg.graphics.beginFill(0x2E80C2, 0.08);



                        rBg.graphics.drawRoundRect(8, 1, secW - 16, rowH - 2, 6, 6);



                        rBg.graphics.endFill();



                    }



                }



            });



            row.addEventListener(MouseEvent.ROLL_OUT, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var rBg:Shape = targetRow.getChildAt(0) as Shape;



                    if (rBg != null)



                    {



                        rBg.graphics.clear();



                        rBg.graphics.beginFill(0xFFFFFF, 0.001);



                        rBg.graphics.drawRect(0, 0, secW, rowH);



                        rBg.graphics.endFill();



                    }



                }



            });



            row.name = String(item.key);



            row.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var flagKey:String = targetRow.name;



                    var rowCb:SimsCheckbox = selfRef.mGenealogyCheckboxesByKey[flagKey] as SimsCheckbox;



                    if (rowCb != null)



                    {



                        var curSt:Boolean = rowCb.getState();



                        rowCb.setState(!curSt);



                        selfRef.onGenealogyToggleClick(flagKey, !curSt);



                    }



                }



            });



            container.addChild(row);



        }



    }



    public function refreshGenealogyDepthBtns():void



    {



        if (this.mGenealogyDepthBtns != null)



        {



            for (var i:int = 0; i < this.mGenealogyDepthBtns.length; i++)



            {



                var dBtn:SimsPillButton = this.mGenealogyDepthBtns[i] as SimsPillButton;



                if (dBtn != null)



                {



                    var dVal:int = parseInt(dBtn.name);



                    dBtn.setSelected(dVal == this.mGenealogyDepth);



                }



            }



        }



    }



    public function applyGenealogyDepth(val:int):void



    {



        this.mGenealogyDepth = val;



        this.refreshGenealogyDepthBtns();



        ExternalInterface.call("CallGameService", "PostServerCommand", {



            "command": "synapse.set_genealogy_depth",



            "commandArgs": [String(val)]



        });



    }



    public function onGenealogyToggleClick(flagKey:String, newState:Boolean):void



    {



        this.mGenealogyFlagsState[flagKey] = newState;



        ExternalInterface.call("CallGameService", "PostServerCommand", {



            "command": "synapse.set_genealogy_flag",



            "commandArgs": [flagKey, newState ? "1" : "0"]



        });



    }



    public function onBulkGenealogyActionClick(action:String):void



    {



        var groups:Array = this.getGenealogyGroups();



        for (var g:int = 0; g < groups.length; g++)



        {



            var grpItems:Array = groups[g].items as Array;



            if (grpItems != null)



            {



                for (var i:int = 0; i < grpItems.length; i++)



                {



                    var k:String = String(grpItems[i].key);



                    var newVal:Boolean = (action != "disable_all");



                    this.mGenealogyFlagsState[k] = newVal;



                    if (this.mGenealogyCheckboxesByKey[k] != null)



                    {



                        var cb:SimsCheckbox = this.mGenealogyCheckboxesByKey[k] as SimsCheckbox;



                        if (cb != null)



                        {



                            cb.setState(newVal);



                        }



                    }



                }



            }



        }



        var actParam:String = (action == "disable_all") ? "all_off" : ((action == "enable_all") ? "all_on" : "default");



        ExternalInterface.call("CallGameService", "PostServerCommand", {



            "command": "synapse.bulk_genealogy_flags",



            "commandArgs": [actParam]



        });



    }



    private function buildWorkspace():void



    {



        this.mWorkspace = new Sprite();



        this.mWorkspace.x = WORKSPACE_X;



        this.mWorkspace.y = HEADER_H;



        this.mWindow.addChild(this.mWorkspace);



        // Build Lore and Biography section directly into workspace



        this.buildLoreSection();



        this.buildContextSection();



        this.buildAutonomySection();



        this.buildGenealogySection();



        this.buildMemorySection();



        this.buildModsSection();



        this.buildDisplaySection();



        this.buildDirectorSection();

        this.buildSimplifiedSection();



        this.buildWorldsSection();



        this.buildExperimentalSection();



        // Footer button: "Готово" (Закрыть)



        var btnW:Number = 200;



        var btnH:Number = 36;



        var btnY:Number = WIN_H - FOOTER_H + Math.round((FOOTER_H - btnH) * 0.5);



        var btnDone:SimsPillButton = new SimsPillButton("Готово", btnW, btnH, "footer_action", "close", this, true);



        btnDone.x = WIN_W - btnW - 20;



        btnDone.y = btnY;



        this.mWindow.addChild(btnDone);



    }



    public function selectTab(index:int):void



    {



        this.closeActivePopup();



        this.closeDirectorModal();



        for (var i:int = 0; i < this.mTabs.length; i++)



        {



            var t:SidebarTab = this.mTabs[i] as SidebarTab;



            if (t != null)



            {



                t.setActive(i == index);



            }



        }



        if (this.mLoreContainer != null)



        {



            this.mLoreContainer.visible = (index == 0);



        }



        if (this.mContextContainer != null)



        {



            this.mContextContainer.visible = (index == 1);



            if (index == 1)



            {



                this.rebuildContextItems();



            }



        }



        if (this.mAutonomyContainer != null)



        {



            this.mAutonomyContainer.visible = (index == 2);



            if (index == 2)



            {



                this.refreshAutonomyUI();



            }



        }



        if (this.mGenealogyContainer != null)



        {



            this.mGenealogyContainer.visible = (index == 3);



            if (index == 3)



            {



                this.rebuildGenealogyItems();



            }



        }



        if (this.mMemoryContainer != null)



        {



            this.mMemoryContainer.visible = (index == 4);



            if (index == 4)



            {



                this.rebuildMemoryItems();



            }



        }



        if (this.mModsContainer != null)



        {



            this.mModsContainer.visible = (index == 5);



            if (index == 5)



            {



                this.rebuildModsItems();



            }



        }



        if (this.mDisplayContainer != null)



        {



            this.mDisplayContainer.visible = (index == 6);



            if (index == 6)



            {



                this.rebuildDisplayItems();



            }



        }



        if (this.mDirectorContainer != null)



        {



            this.mDirectorContainer.visible = (index == 7);



            if (index == 7)



            {



                this.refreshDirectorUI();



            }



        }



                if (this.mSimplifiedContainer != null)
        {
            this.mSimplifiedContainer.visible = (index == 8);
            if (index == 8)
            {
                this.refreshSimplifiedUI();
            }
        }
if (this.mWorldsContainer != null)



        {



            this.mWorldsContainer.visible = (index == 9);



            if (index == 9)



            {



                this.selectWorld(this.mCurrentWorldKey || this.mActiveLotWorldKey || "Виллоу Крик");



            }



        }



        if (this.mExperimentalContainer != null)



        {



            this.mExperimentalContainer.visible = (index == 10);



            if (index == 10)



            {



                this.rebuildExperimentalItems();



            }



        }



    }



    private function centerWindow():void



    {



        if (!this.mWindow) return;



        var sw:Number = stage ? stage.stageWidth : 1920;



        var sh:Number = stage ? stage.stageHeight : 1080;



        this.mBaseX = Math.round((sw - WIN_W) * 0.5);



        this.mBaseY = Math.round((sh - WIN_H) * 0.5);



        this.mWindow.x = this.mBaseX;



        this.mWindow.y = this.mBaseY;



    }



    private function onDragMove(e:MouseEvent):void



    {



        if (this.mDragging && stage && this.mWindow)



        {



            this.mBaseX = stage.mouseX - this.mDragX;



            this.mBaseY = stage.mouseY - this.mDragY;



            this.mWindow.x = this.mBaseX;



            this.mWindow.y = this.mBaseY;



        }



    }



    public static function makeText(str:String, size:int, color:uint):TextField



    {



        var tf:TextField = new TextField();



        tf.embedFonts = true;



        tf.selectable = false;



        tf.mouseEnabled = false;



        tf.autoSize = TextFieldAutoSize.LEFT;



        var fmt:TextFormat = new TextFormat("$TextFont", size, color, false);



        tf.defaultTextFormat = fmt;



        tf.text = str;



        return tf;



    }



    public static function makeCenteredText(str:String, size:int, color:uint, boxW:Number):TextField



    {



        var tf:TextField = new TextField();



        tf.embedFonts = true;



        tf.selectable = false;



        tf.mouseEnabled = false;



        tf.width = boxW;



        tf.height = size + 10;



        tf.autoSize = TextFieldAutoSize.NONE;



        var fmt:TextFormat = new TextFormat("$TextFont", size, color, false);



        fmt.align = "center";



        tf.defaultTextFormat = fmt;



        tf.text = str;



        return tf;



    }



    public static function makeBoundedText(str:String, size:int, color:uint, maxW:Number):TextField



    {



        var tf:TextField = new TextField();



        tf.embedFonts = true;



        tf.selectable = false;



        tf.mouseEnabled = false;



        tf.autoSize = TextFieldAutoSize.NONE;



        tf.width = maxW;



        tf.height = size + 10;



        var fmt:TextFormat = new TextFormat("$TextFont", size, color, false);



        tf.defaultTextFormat = fmt;



        tf.text = str;



        if (tf.textWidth > maxW - 4)



        {



            var curStr:String = str;



            while (curStr.length > 3 && tf.textWidth > maxW - 4)



            {



                curStr = curStr.substr(0, curStr.length - 1);



                tf.text = curStr + "...";



            }



        }



        return tf;



    }



    // =========================================================================



    // MEMORY & CONVERSATION HISTORY SECTION & LOGIC



    // =========================================================================



    public function parseMemoryState(packedStr:String):void



    {



        if (packedStr && packedStr != "00" && packedStr != "")



        {



            var pairs:Array = packedStr.split(";");



            for (var i:int = 0; i < pairs.length; i++)



            {



                var pStr:String = String(pairs[i]);



                if (!pStr) continue;



                var kv:Array = pStr.split(":");



                var k:String = String(kv[0]);



                var v:String = String(kv[1]);



                if (k == "ev_mem")



                {



                    this.mEventMemoryEnabled = (v == "1");



                }



                else if (k == "diag_hours")



                {



                    var hVal:int = parseInt(v);



                    if (hVal >= 0) this.mDialogueMemoryHours = hVal;



                }



                else if (k == "sum_pers")



                {



                    this.mSummarizePersonal = (v == "1");



                }



                else if (k == "sum_grp")



                {



                    this.mSummarizeGroup = (v == "1");



                }



            }



        }



    }



    public function buildMemorySection():void



    {



        this.mMemoryContainer = new Sprite();



        this.mMemoryContainer.visible = false;



        this.mWorkspace.addChild(this.mMemoryContainer);



        var secW:Number = WORKSPACE_W;



        var barH:Number = 28;



        var secY:Number = 0;



        var secBodyH:Number = 430;



        var selfRef:SettingsUI = this;



        this.drawSectionContainerOn(this.mMemoryContainer, secY, secW, barH, secBodyH);



        var secTitle:TextField = makeCenteredText("Память, события и история общения персонажа", 13, 0xFFFFFF, secW);



        secTitle.x = 0;



        secTitle.y = secY + 4;



        this.mMemoryContainer.addChild(secTitle);



        var hintBg:Shape = new Shape();



        var hMat:Matrix = new Matrix();



        hMat.createGradientBox(secW - 24, 26, Math.PI / 2, 0, 0);



        hintBg.graphics.beginGradientFill(



            GradientType.LINEAR,



            [0xECF3FA, 0xDFEAF4],



            [1.0, 1.0],



            [0, 255],



            hMat



        );



        hintBg.graphics.lineStyle(1, 0xB8CBDC, 0.8, true);



        hintBg.graphics.drawRoundRect(12, secY + barH + 6, secW - 24, 26, 6, 6);



        hintBg.graphics.endFill();



        this.mMemoryContainer.addChild(hintBg);



        var hintTf:TextField = makeText("Управление автоматической памятью событий, горизонтом диалогов и суммаризацией.", 11, 0x1E466B);



        hintTf.x = 22;



        hintTf.y = secY + barH + 11;



        this.mMemoryContainer.addChild(hintTf);



        var scrollW:Number = secW - 24;



        var scrollH:Number = secBodyH - 42;



        this.mMemoryScrollView = new MaxisScrollView(scrollW, scrollH);



        this.mMemoryScrollView.x = 12;



        this.mMemoryScrollView.y = secY + barH + 36;



        this.mMemoryContainer.addChild(this.mMemoryScrollView);



        var bottomCap:Shape = new Shape();



        bottomCap.graphics.beginFill(0xFFFFFF, 1.0);



        bottomCap.graphics.drawRoundRect(1, secY + barH + secBodyH - 8, secW - 2, 7, 4, 4);



        bottomCap.graphics.endFill();



        this.mMemoryContainer.addChild(bottomCap);



    }



    public function reflowMemoryAccordions():void



    {



        var currY:Number = 0;



        var gap:Number = 6;



        for (var i:int = 0; i < this.mMemoryAccordionSections.length; i++)



        {



            var sec:MaxisAccordionSection = this.mMemoryAccordionSections[i] as MaxisAccordionSection;



            if (sec != null)



            {



                sec.y = currY;



                currY += sec.getTotalHeight() + gap;



            }



        }



        if (this.mMemoryScrollView != null)



        {



            this.mMemoryScrollView.updateLayout(currY);



        }



    }



    public function getMemoryGroups():Array



    {



        return [



            {



                "title": "1. АВТОМАТИЧЕСКАЯ ПАМЯТЬ СОБЫТИЙ",



                "items": [



                    {



                        "key": "event_memory_enabled",



                        "title": "Автоматическая память событий жизни",



                        "desc": "Фиксация ключевых событий: романтика, измены, помолвки, браки, драки, пожары, смерть, карьера."



                    }



                ]



            },



            {



                "title": "2. ГОРИЗОНТ ПАМЯТИ ДИАЛОГОВ И СООБЩЕНИЙ",



                "is_hours_section": true,



                "items": []



            },



            {



                "title": "3. ИИ-СУММАРИЗАЦИЯ ПЕРЕПИСКИ (ПК)",



                "items": [



                    {



                        "key": "summarize_personal",



                        "title": "Суммаризация личной переписки 1-на-1",



                        "desc": "Создавать воспоминание с выжимкой диалога при закрытии окна мессенджера за ПК."



                    },



                    {



                        "key": "summarize_group",



                        "title": "Суммаризация групповых чатов",



                        "desc": "Создавать воспоминание с выжимкой переписки при закрытии группового окна за ПК."



                    }



                ]



            },



            {



                "title": "4. ОЧИСТКА И УПРАВЛЕНИЕ ПАМЯТЬЮ",



                "is_actions_section": true,



                "items": []



            },



            {



                "title": "5. СОЗДАНИЕ ВОСПОМИНАНИЯ (ПАМЯТИ)",



                "is_create_memory_section": true,



                "items": []



            }



        ];



    }



    public function rebuildMemoryItems():void



    {



        if (!this.mMemoryScrollView) return;



        var prevScroll:Number = this.mMemoryScrollView.getScrollY();



        var scrollContent:Sprite = this.mMemoryScrollView.getContent();



        while (scrollContent.numChildren > 0)



        {



            scrollContent.removeChildAt(0);



        }



        this.mMemoryAccordionSections = [];



        this.mMemoryCheckboxesByKey = {};



        this.mMemoryHoursBtns = [];



        var groups:Array = this.getMemoryGroups();



        var secW:Number = this.mMemoryScrollView.getViewportWidth();



        var selfRef:SettingsUI = this;



        for (var gIdx:int = 0; gIdx < groups.length; gIdx++)



        {



            var grp:Object = groups[gIdx];



            var secTitle:String = String(grp.title);



            var secKey:String = "mem_" + secTitle;



            var isInitiallyExpanded:Boolean = (this.mMemoryExpandedSections[secKey] !== undefined) ?



                Boolean(this.mMemoryExpandedSections[secKey]) : true;



            var accSec:MaxisAccordionSection = new MaxisAccordionSection(



                secTitle,



                secW,



                28,



                isInitiallyExpanded,



                function(tSec:MaxisAccordionSection):void {



                    var k:String = "mem_" + tSec.title;



                    selfRef.mMemoryExpandedSections[k] = tSec.isExpanded;



                    selfRef.reflowMemoryAccordions();



                }



            );



            var startRowY:Number = 0;



            if (grp.is_hours_section === true)



            {



                var hoursRow:Sprite = new Sprite();



                hoursRow.x = 0;



                hoursRow.y = 0;



                var hoursRowH:Number = 42;



                var hRowBg:Shape = new Shape();



                hRowBg.graphics.beginFill(COL_ICE_BANNER, 0.7);



                hRowBg.graphics.drawRoundRect(10, 2, secW - 20, hoursRowH - 4, 6, 6);



                hRowBg.graphics.endFill();



                hoursRow.addChild(hRowBg);



                var hLabel:TextField = makeText("Срок хранения реплик:", 11, 0x19456B);



                hLabel.x = 18;



                hLabel.y = 11;



                hoursRow.addChild(hLabel);



                var hoursList:Array = [



                    {"label": "24 ч.", "hours": 24, "w": 48},



                    {"label": "48 ч.", "hours": 48, "w": 48},



                    {"label": "72 ч.", "hours": 72, "w": 48},



                    {"label": "168 ч.", "hours": 168, "w": 56},



                    {"label": "999 ч.", "hours": 999, "w": 52},



                    {"label": "Без ограничений", "hours": 0, "w": 120}



                ];



                var hBtnH:Number = 24;



                var currentHX:Number = 165;



                for (var hIdx:int = 0; hIdx < hoursList.length; hIdx++)



                {



                    var hObj:Object = hoursList[hIdx];



                    var hBtnW:Number = Number(hObj.w);



                    var hBtn:SimsPillButton = new SimsPillButton(



                        String(hObj.label),



                        hBtnW,



                        hBtnH,



                        "",



                        "",



                        this,



                        false,



                        11



                    );



                    hBtn.x = currentHX;



                    hBtn.y = 9;



                    hBtn.name = String(hObj.hours);



                    hBtn.setSelected(hObj.hours == this.mDialogueMemoryHours);



                    hBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



                        var targetBtn:Sprite = e.currentTarget as Sprite;



                        if (targetBtn != null)



                        {



                            var targetHours:int = parseInt(targetBtn.name);



                            selfRef.applyDialogueHours(targetHours);



                        }



                    });



                    hoursRow.addChild(hBtn);



                    this.mMemoryHoursBtns.push(hBtn);



                    currentHX += hBtnW + 5;



                }



                accSec.content.addChild(hoursRow);



                startRowY = hoursRowH + 4;



            }



            else if (grp.is_actions_section === true)



            {



                var actRow:Sprite = new Sprite();



                actRow.x = 0;



                actRow.y = 0;



                var actRowH:Number = 48;



                var actRowBg:Shape = new Shape();



                actRowBg.graphics.beginFill(COL_ICE_BANNER, 0.7);



                actRowBg.graphics.drawRoundRect(10, 2, secW - 20, actRowH - 4, 6, 6);



                actRowBg.graphics.endFill();



                actRow.addChild(actRowBg);



                var clrLogBtn:SimsPillButton = new SimsPillButton(



                    "Очистить историю диалогов",



                    220,



                    26,



                    "clr_log",



                    "",



                    this,



                    false,



                    11



                );



                clrLogBtn.x = 20;



                clrLogBtn.y = 10;



                clrLogBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



                    ExternalInterface.call("CallGameService", "PostServerCommand", {



                        "command": "synapse.clear_dialogue_log",



                        "commandArgs": []



                    });



                });



                actRow.addChild(clrLogBtn);



                var clrMemBtn:SimsPillButton = new SimsPillButton(



                    "Очистить долгосрочные воспоминания",



                    250,



                    26,



                    "clr_mem",



                    "",



                    this,



                    false,



                    11



                );



                clrMemBtn.x = 250;



                clrMemBtn.y = 10;



                clrMemBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



                    ExternalInterface.call("CallGameService", "PostServerCommand", {



                        "command": "synapse.clear_longterm_memory",



                        "commandArgs": []



                    });



                });



                actRow.addChild(clrMemBtn);



                accSec.content.addChild(actRow);



                startRowY = actRowH + 4;



            }



            else if (grp.is_create_memory_section === true)



            {



                var memRow:Sprite = new Sprite();



                memRow.x = 0;



                memRow.y = 0;



                var memRowH:Number = 206;



                var memRowBg:Shape = new Shape();



                memRowBg.graphics.beginFill(COL_ICE_BANNER, 0.7);



                memRowBg.graphics.drawRoundRect(10, 2, secW - 20, memRowH - 4, 6, 6);



                memRowBg.graphics.endFill();



                memRow.addChild(memRowBg);



                // 1. Выбор персонажа



                var mPickBtn:SimsPillButton = new SimsPillButton(



                    "ВЫБРАТЬ ПЕРСОНАЖА",



                    165,



                    26,



                    "pick_mem_sim",



                    "",



                    this,



                    false,



                    11



                );



                mPickBtn.x = 20;



                mPickBtn.y = 10;



                mPickBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



                    ExternalInterface.call("CallGameService", "PostServerCommand", {



                        "command": "synapse.pick_memory_sim",



                        "commandArgs": []



                    });



                });



                memRow.addChild(mPickBtn);



                var curMemName:String = (selfRef.mSelectedMemorySimName && selfRef.mSelectedMemorySimName.length > 0) ? selfRef.mSelectedMemorySimName : selfRef.mCurrentSimName;



                var curMemId:String = (selfRef.mSelectedMemorySimId && selfRef.mSelectedMemorySimId.length > 0) ? selfRef.mSelectedMemorySimId : selfRef.mCurrentSimId;



                var initMemSimLabel:String = (curMemName && curMemName.length > 0) ? ("Персонаж: " + curMemName + " [ID: " + curMemId + "]") : "Персонаж: (не выбран)";



                selfRef.mMemorySimLabel = makeText(initMemSimLabel, 12, 0x1A4064);



                selfRef.mMemorySimLabel.x = 195;



                selfRef.mMemorySimLabel.y = 14;



                memRow.addChild(selfRef.mMemorySimLabel);



                // 2. Текст воспоминания



                var memTxtLbl:TextField = makeText("Текст воспоминания:", 11, 0x19456B);



                memTxtLbl.x = 20;



                memTxtLbl.y = 44;



                memRow.addChild(memTxtLbl);



                var memTxtBorder:Shape = new Shape();



                memTxtBorder.graphics.beginFill(COL_BOX_BORDER, 1.0);



                memTxtBorder.graphics.drawRoundRect(20, 62, secW - 40, 56, 5, 5);



                memTxtBorder.graphics.endFill();



                memRow.addChild(memTxtBorder);



                var memTxtInner:Shape = new Shape();



                memTxtInner.graphics.beginFill(0xFFFFFF, 1.0);



                memTxtInner.graphics.drawRoundRect(21, 63, secW - 42, 54, 4, 4);



                memTxtInner.graphics.endFill();



                memRow.addChild(memTxtInner);



                selfRef.mMemoryTextInput = new TextField();



                selfRef.mMemoryTextInput.type = "input";



                selfRef.mMemoryTextInput.embedFonts = true;



                selfRef.mMemoryTextInput.selectable = true;



                selfRef.mMemoryTextInput.mouseEnabled = true;



                selfRef.mMemoryTextInput.multiline = true;



                selfRef.mMemoryTextInput.wordWrap = true;



                selfRef.mMemoryTextInput.x = 24;



                selfRef.mMemoryTextInput.y = 65;



                selfRef.mMemoryTextInput.width = secW - 48;



                selfRef.mMemoryTextInput.height = 50;



                var memTfFmt:TextFormat = new TextFormat("$TextFont", 12, COL_LABEL_DARK, false);



                memTfFmt.leading = 2;



                selfRef.mMemoryTextInput.defaultTextFormat = memTfFmt;



                selfRef.mMemoryTextInput.setTextFormat(memTfFmt);



                selfRef.mMemoryTextInput.maxChars = 600;



                selfRef.mMemoryTextInput.addEventListener(FocusEvent.FOCUS_IN, function(e:FocusEvent):void {



                    try {



                        var cmFiM:Object = getDefinitionByName("olympus.io.CommunicationManager");



                        cmFiM.CallGameService("SetTextFieldInput", true);



                    } catch(eFiM:Error) {}



                });



                selfRef.mMemoryTextInput.addEventListener(FocusEvent.FOCUS_OUT, function(e:FocusEvent):void {



                    try {



                        var cmFoM:Object = getDefinitionByName("olympus.io.CommunicationManager");



                        cmFoM.CallGameService("SetTextFieldInput", false);



                    } catch(eFoM:Error) {}



                });



                memRow.addChild(selfRef.mMemoryTextInput);



                // 3. Срок хранения (дней)



                var daysLbl:TextField = makeText("Срок хранения (дней):", 11, 0x19456B);



                daysLbl.x = 20;



                daysLbl.y = 127;



                memRow.addChild(daysLbl);



                var daysBorder:Shape = new Shape();



                daysBorder.graphics.beginFill(COL_BOX_BORDER, 1.0);



                daysBorder.graphics.drawRoundRect(155, 124, 54, 22, 4, 4);



                daysBorder.graphics.endFill();



                memRow.addChild(daysBorder);



                var daysInner:Shape = new Shape();



                daysInner.graphics.beginFill(0xFFFFFF, 1.0);



                daysInner.graphics.drawRoundRect(156, 125, 52, 20, 3, 3);



                daysInner.graphics.endFill();



                memRow.addChild(daysInner);



                selfRef.mMemoryDaysInput = new TextField();



                selfRef.mMemoryDaysInput.type = "input";



                selfRef.mMemoryDaysInput.embedFonts = true;



                selfRef.mMemoryDaysInput.selectable = true;



                selfRef.mMemoryDaysInput.mouseEnabled = true;



                selfRef.mMemoryDaysInput.multiline = false;



                selfRef.mMemoryDaysInput.restrict = "0-9";



                selfRef.mMemoryDaysInput.maxChars = 4;



                selfRef.mMemoryDaysInput.text = "0";



                selfRef.mMemoryDaysInput.x = 158;



                selfRef.mMemoryDaysInput.y = 126;



                selfRef.mMemoryDaysInput.width = 48;



                selfRef.mMemoryDaysInput.height = 18;



                selfRef.mMemoryDaysInput.defaultTextFormat = memTfFmt;



                selfRef.mMemoryDaysInput.setTextFormat(memTfFmt);



                selfRef.mMemoryDaysInput.addEventListener(FocusEvent.FOCUS_IN, function(e:FocusEvent):void {



                    try {



                        var cmFiD:Object = getDefinitionByName("olympus.io.CommunicationManager");



                        cmFiD.CallGameService("SetTextFieldInput", true);



                    } catch(eFiD:Error) {}



                });



                selfRef.mMemoryDaysInput.addEventListener(FocusEvent.FOCUS_OUT, function(e:FocusEvent):void {



                    try {



                        var cmFoD:Object = getDefinitionByName("olympus.io.CommunicationManager");



                        cmFoD.CallGameService("SetTextFieldInput", false);



                    } catch(eFoD:Error) {}



                });



                memRow.addChild(selfRef.mMemoryDaysInput);



                var daysHint:TextField = makeText("(0 = навсегда / бессрочно)", 11, 0x556677);



                daysHint.x = 216;



                daysHint.y = 127;



                memRow.addChild(daysHint);



                // 4. Кнопка сохранения и бейдж



                var saveMemBtn:SimsPillButton = new SimsPillButton(



                    "СОХРАНИТЬ ВОСПОМИНАНИЕ",



                    210,



                    28,



                    "save_mem",



                    "",



                    this,



                    false,



                    11



                );



                saveMemBtn.x = 20;



                saveMemBtn.y = 158;



                saveMemBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



                    var targetSid:String = (selfRef.mSelectedMemorySimId && selfRef.mSelectedMemorySimId.length > 0) ? selfRef.mSelectedMemorySimId : selfRef.mCurrentSimId;



                    var memTxt:String = selfRef.mMemoryTextInput ? selfRef.mMemoryTextInput.text : "";



                    var daysVal:String = selfRef.mMemoryDaysInput ? selfRef.mMemoryDaysInput.text : "0";



                    if (memTxt != null && memTxt.length > 0 && targetSid != null && targetSid != "0")



                    {



                        ExternalInterface.call("CallGameService", "PostServerCommand", {



                            "command": "synapse.create_custom_memory",



                            "commandArgs": [targetSid, daysVal, selfRef.encodeSafeStr(memTxt)]



                        });



                    }



                });



                memRow.addChild(saveMemBtn);



                selfRef.mMemoryCreatedBadge = makeText("Воспоминание сохранено!", 11, 0x1E824C);



                selfRef.mMemoryCreatedBadge.x = 240;



                selfRef.mMemoryCreatedBadge.y = 164;



                selfRef.mMemoryCreatedBadge.visible = false;



                memRow.addChild(selfRef.mMemoryCreatedBadge);



                accSec.content.addChild(memRow);



                startRowY = memRowH + 4;



            }



            var grpItems:Array = grp.items as Array;



            if (grpItems != null && grpItems.length > 0)



            {



                this.populateMemorySectionItems(accSec.content, grpItems, secW, startRowY);



            }



            scrollContent.addChild(accSec);



            this.mMemoryAccordionSections.push(accSec);



        }



        this.mMemoryScrollView.setOwnerSections(this.mMemoryAccordionSections);



        this.reflowMemoryAccordions();



        if (prevScroll > 0)



        {



            this.mMemoryScrollView.scrollTo(prevScroll);



        }



        else



        {



            this.mMemoryScrollView.resetScroll();



        }



    }



    private function populateMemorySectionItems(container:Sprite, items:Array, secW:Number, startY:Number = 0):void



    {



        var rowH:Number = 40;



        var selfRef:SettingsUI = this;



        for (var i:int = 0; i < items.length; i++)



        {



            var item:Object = items[i];



            var row:Sprite = new Sprite();



            row.y = startY + i * rowH;



            row.buttonMode = true;



            row.useHandCursor = true;



            row.mouseChildren = true;



            var rowBg:Shape = new Shape();



            rowBg.graphics.beginFill(0xFFFFFF, 0.001);



            rowBg.graphics.drawRect(0, 0, secW, rowH);



            rowBg.graphics.endFill();



            row.addChild(rowBg);



            var sep:Shape = new Shape();



            sep.graphics.lineStyle(1, 0xCBD6E2, 0.40);



            sep.graphics.moveTo(16, rowH - 1);



            sep.graphics.lineTo(secW - 16, rowH - 1);



            row.addChild(sep);



            var titleTf:TextField = makeBoundedText(String(item.title), 12, 0x19456B, secW - 75);



            titleTf.x = 20;



            titleTf.y = 4;



            row.addChild(titleTf);



            var descTf:TextField = makeBoundedText(String(item.desc), 10, 0x647B91, secW - 75);



            descTf.x = 20;



            descTf.y = 20;



            row.addChild(descTf);



            var isFlagOn:Boolean = true;



            if (item.key == "event_memory_enabled")



            {



                isFlagOn = this.mEventMemoryEnabled;



            }



            else if (item.key == "summarize_personal")



            {



                isFlagOn = this.mSummarizePersonal;



            }



            else if (item.key == "summarize_group")



            {



                isFlagOn = this.mSummarizeGroup;



            }



            var cb:SimsCheckbox = new SimsCheckbox(String(item.key), isFlagOn, function(k:String, st:Boolean):void {



                selfRef.onMemoryToggleClick(k, st);



            });



            cb.x = secW - 46;



            cb.y = Math.floor((rowH - 20) / 2);



            row.addChild(cb);



            this.mMemoryCheckboxesByKey[item.key] = cb;



            row.addEventListener(MouseEvent.ROLL_OVER, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var rBg:Shape = targetRow.getChildAt(0) as Shape;



                    if (rBg != null)



                    {



                        rBg.graphics.clear();



                        rBg.graphics.beginFill(0x2E80C2, 0.08);



                        rBg.graphics.drawRoundRect(8, 1, secW - 16, rowH - 2, 6, 6);



                        rBg.graphics.endFill();



                    }



                }



            });



            row.addEventListener(MouseEvent.ROLL_OUT, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var rBg:Shape = targetRow.getChildAt(0) as Shape;



                    if (rBg != null)



                    {



                        rBg.graphics.clear();



                        rBg.graphics.beginFill(0xFFFFFF, 0.001);



                        rBg.graphics.drawRect(0, 0, secW, rowH);



                        rBg.graphics.endFill();



                    }



                }



            });



            row.name = String(item.key);



            row.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var flagKey:String = targetRow.name;



                    var rowCb:SimsCheckbox = selfRef.mMemoryCheckboxesByKey[flagKey] as SimsCheckbox;



                    if (rowCb != null)



                    {



                        var curSt:Boolean = rowCb.getState();



                        rowCb.setState(!curSt);



                        selfRef.onMemoryToggleClick(flagKey, !curSt);



                    }



                }



            });



            container.addChild(row);



        }



    }



    public function onMemoryToggleClick(flagKey:String, newState:Boolean):void



    {



        if (flagKey == "event_memory_enabled")



        {



            this.mEventMemoryEnabled = newState;



            ExternalInterface.call("CallGameService", "PostServerCommand", {



                "command": "synapse.set_event_memory",



                "commandArgs": [newState ? "1" : "0"]



            });



        }



        else if (flagKey == "summarize_personal" || flagKey == "summarize_group")



        {



            if (flagKey == "summarize_personal") this.mSummarizePersonal = newState;



            if (flagKey == "summarize_group") this.mSummarizeGroup = newState;



            ExternalInterface.call("CallGameService", "PostServerCommand", {



                "command": "synapse.update_chat_flag",



                "commandArgs": [flagKey, newState ? "1" : "0"]



            });



        }



    }



    public function applyDialogueHours(val:int):void



    {



        this.mDialogueMemoryHours = val;



        this.refreshMemoryHoursBtns();



        ExternalInterface.call("CallGameService", "PostServerCommand", {



            "command": "synapse.set_dialogue_hours",



            "commandArgs": [String(val)]



        });



    }



    public function refreshMemoryHoursBtns():void



    {



        if (this.mMemoryHoursBtns != null)



        {



            for (var i:int = 0; i < this.mMemoryHoursBtns.length; i++)



            {



                var hBtn:SimsPillButton = this.mMemoryHoursBtns[i] as SimsPillButton;



                if (hBtn != null)



                {



                    var hVal:int = parseInt(hBtn.name);



                    hBtn.setSelected(hVal == this.mDialogueMemoryHours);



                }



            }



        }



    }



    // =========================================================================



    // MODS INTEGRATION SECTION & LOGIC



    // =========================================================================



    public function parseModsState(packedStr:String):void



    {



        if (packedStr && packedStr != "00" && packedStr != "")



        {



            var pairs:Array = packedStr.split(";");



            for (var i:int = 0; i < pairs.length; i++)



            {



                var pStr:String = String(pairs[i]);



                if (!pStr) continue;



                var kv:Array = pStr.split(":");



                var k:String = String(kv[0]);



                var v:String = String(kv[1]);



                if (k == "ww_mode")



                {



                    this.mWwSexMode = v;



                }



            }



        }



    }



    public function buildModsSection():void



    {



        this.mModsContainer = new Sprite();



        this.mModsContainer.visible = false;



        this.mWorkspace.addChild(this.mModsContainer);



        var secW:Number = WORKSPACE_W;



        var barH:Number = 28;



        var secY:Number = 0;



        var secBodyH:Number = 430;



        var selfRef:SettingsUI = this;



        this.drawSectionContainerOn(this.mModsContainer, secY, secW, barH, secBodyH);



        var secTitle:TextField = makeCenteredText("Интеграция со сторонними модами", 13, 0xFFFFFF, secW);



        secTitle.x = 0;



        secTitle.y = secY + 4;



        this.mModsContainer.addChild(secTitle);



        var hintBg:Shape = new Shape();



        var hMat:Matrix = new Matrix();



        hMat.createGradientBox(secW - 24, 26, Math.PI / 2, 0, 0);



        hintBg.graphics.beginGradientFill(



            GradientType.LINEAR,



            [0xECF3FA, 0xDFEAF4],



            [1.0, 1.0],



            [0, 255],



            hMat



        );



        hintBg.graphics.lineStyle(1, 0xB8CBDC, 0.8, true);



        hintBg.graphics.drawRoundRect(12, secY + barH + 6, secW - 24, 26, 6, 6);



        hintBg.graphics.endFill();



        this.mModsContainer.addChild(hintBg);



        var hintTf:TextField = makeText("Настройка взаимодействия с установленными модами The Sims 4.", 11, 0x1E466B);



        hintTf.x = 22;



        hintTf.y = secY + barH + 11;



        this.mModsContainer.addChild(hintTf);



        var scrollW:Number = secW - 24;



        var scrollH:Number = secBodyH - 42;



        this.mModsScrollView = new MaxisScrollView(scrollW, scrollH);



        this.mModsScrollView.x = 12;



        this.mModsScrollView.y = secY + barH + 36;



        this.mModsContainer.addChild(this.mModsScrollView);



        var bottomCap:Shape = new Shape();



        bottomCap.graphics.beginFill(0xFFFFFF, 1.0);



        bottomCap.graphics.drawRoundRect(1, secY + barH + secBodyH - 8, secW - 2, 7, 4, 4);



        bottomCap.graphics.endFill();



        this.mModsContainer.addChild(bottomCap);



    }



    public function reflowModsAccordions():void



    {



        var currY:Number = 0;



        var gap:Number = 6;



        for (var i:int = 0; i < this.mModsAccordionSections.length; i++)



        {



            var sec:MaxisAccordionSection = this.mModsAccordionSections[i] as MaxisAccordionSection;



            if (sec != null)



            {



                sec.y = currY;



                currY += sec.getTotalHeight() + gap;



            }



        }



        if (this.mModsScrollView != null)



        {



            this.mModsScrollView.updateLayout(currY);



        }



    }



    public function getModsGroups():Array



    {



        return [



            {



                "title": "1. ИНТЕГРАЦИЯ WICKEDWHIMS",



                "options": [



                    {



                        "key": "bed_picker",



                        "title": "Кровать (с выбором поз)",



                        "desc": "Персонажи идут к свободной кровати в доме и открывается меню выбора анимаций WickedWhims."



                    },



                    {



                        "key": "nearby_picker",



                        "title": "Ближайший объект (с выбором поз)",



                        "desc": "Симы используют ближайший подходящий объект (кровать, диван, пол и т.д.) и открывают меню поз."



                    },



                    {



                        "key": "auto_bed",



                        "title": "Кровать (случайная поза / авто-старт)",



                        "desc": "Секс начинается на кровати сразу со случайной анимацией без открытия меню поз."



                    },



                    {



                        "key": "auto_nearby",



                        "title": "Ближайший объект (случайная поза / авто-старт)",



                        "desc": "Секс начинается на ближайшем объекте сразу со случайной анимацией без открытия меню поз."



                    }



                ]



            }



        ];



    }



    public function rebuildModsItems():void



    {



        if (!this.mModsScrollView) return;



        var prevScroll:Number = this.mModsScrollView.getScrollY();



        var scrollContent:Sprite = this.mModsScrollView.getContent();



        while (scrollContent.numChildren > 0)



        {



            scrollContent.removeChildAt(0);



        }



        this.mModsAccordionSections = [];



        this.mModsOptionRowsByKey = {};



        this.mModsOptionIndicatorsByKey = {};



        var groups:Array = this.getModsGroups();



        var secW:Number = this.mModsScrollView.getViewportWidth();



        var selfRef:SettingsUI = this;



        for (var gIdx:int = 0; gIdx < groups.length; gIdx++)



        {



            var grp:Object = groups[gIdx];



            var secTitle:String = String(grp.title);



            var secKey:String = "mods_" + secTitle;



            var isInitiallyExpanded:Boolean = (this.mModsExpandedSections[secKey] !== undefined) ?



                Boolean(this.mModsExpandedSections[secKey]) : true;



            var accSec:MaxisAccordionSection = new MaxisAccordionSection(



                secTitle,



                secW,



                28,



                isInitiallyExpanded,



                function(tSec:MaxisAccordionSection):void {



                    var k:String = "mods_" + tSec.title;



                    selfRef.mModsExpandedSections[k] = tSec.isExpanded;



                    selfRef.reflowModsAccordions();



                }



            );



            // Subheader banner note



            var noteRow:Sprite = new Sprite();



            noteRow.x = 0;



            noteRow.y = 0;



            var noteH:Number = 32;



            var nBg:Shape = new Shape();



            nBg.graphics.beginFill(COL_ICE_BANNER, 0.6);



            nBg.graphics.drawRoundRect(10, 2, secW - 20, noteH - 4, 6, 6);



            nBg.graphics.endFill();



            noteRow.addChild(nBg);



            var nTf:TextField = makeText("Поведение персонажей при вызове действия [DO=wicked_sex]:", 11, 0x19456B);



            nTf.x = 18;



            nTf.y = 7;



            noteRow.addChild(nTf);



            accSec.content.addChild(noteRow);



            var grpOptions:Array = grp.options as Array;



            if (grpOptions != null && grpOptions.length > 0)



            {



                this.populateWwIntimacyOptions(accSec.content, grpOptions, secW, noteH + 4);



            }



            scrollContent.addChild(accSec);



            this.mModsAccordionSections.push(accSec);



        }



        this.mModsScrollView.setOwnerSections(this.mModsAccordionSections);



        this.reflowModsAccordions();



        if (prevScroll > 0)



        {



            this.mModsScrollView.scrollTo(prevScroll);



        }



        else



        {



            this.mModsScrollView.resetScroll();



        }



    }



    private function populateWwIntimacyOptions(container:Sprite, options:Array, secW:Number, startY:Number = 0):void



    {



        var rowH:Number = 46;



        var selfRef:SettingsUI = this;



        for (var i:int = 0; i < options.length; i++)



        {



            var item:Object = options[i];



            var row:Sprite = new Sprite();



            row.y = startY + i * rowH;



            row.buttonMode = true;



            row.useHandCursor = true;



            row.mouseChildren = false;



            var rowBg:Shape = new Shape();



            rowBg.graphics.beginFill(0xFFFFFF, 0.001);



            rowBg.graphics.drawRect(0, 0, secW, rowH);



            rowBg.graphics.endFill();



            row.addChild(rowBg);



            var sep:Shape = new Shape();



            sep.graphics.lineStyle(1, 0xCBD6E2, 0.40);



            sep.graphics.moveTo(16, rowH - 1);



            sep.graphics.lineTo(secW - 16, rowH - 1);



            row.addChild(sep);



            var titleTf:TextField = makeBoundedText(String(item.title), 12, 0x19456B, secW - 120);



            titleTf.x = 20;



            titleTf.y = 5;



            row.addChild(titleTf);



            var descTf:TextField = makeBoundedText(String(item.desc), 10, 0x647B91, secW - 120);



            descTf.x = 20;



            descTf.y = 23;



            row.addChild(descTf);



            // Badge indicator



            var badgeW:Number = 88;



            var badgeH:Number = 24;



            var badge:Sprite = new Sprite();



            badge.x = secW - badgeW - 20;



            badge.y = Math.floor((rowH - badgeH) / 2);



            row.addChild(badge);



            this.mModsOptionIndicatorsByKey[item.key] = badge;



            this.mModsOptionRowsByKey[item.key] = row;



            this.drawOptionBadge(badge, badgeW, badgeH, item.key == this.mWwSexMode);



            row.addEventListener(MouseEvent.ROLL_OVER, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var rBg:Shape = targetRow.getChildAt(0) as Shape;



                    if (rBg != null)



                    {



                        rBg.graphics.clear();



                        rBg.graphics.beginFill(0x2E80C2, 0.08);



                        rBg.graphics.drawRoundRect(8, 1, secW - 16, rowH - 2, 6, 6);



                        rBg.graphics.endFill();



                    }



                }



            });



            row.addEventListener(MouseEvent.ROLL_OUT, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var rBg:Shape = targetRow.getChildAt(0) as Shape;



                    if (rBg != null)



                    {



                        rBg.graphics.clear();



                        rBg.graphics.beginFill(0xFFFFFF, 0.001);



                        rBg.graphics.drawRect(0, 0, secW, rowH);



                        rBg.graphics.endFill();



                    }



                }



            });



            row.name = String(item.key);



            row.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var optKey:String = targetRow.name;



                    selfRef.applyWwSexMode(optKey);



                }



            });



            container.addChild(row);



        }



    }



    private function drawOptionBadge(badge:Sprite, w:Number, h:Number, isSelected:Boolean):void



    {



        while (badge.numChildren > 0)



        {



            badge.removeChildAt(0);



        }



        var bShape:Shape = new Shape();



        var mat:Matrix = new Matrix();



        mat.createGradientBox(w, h, Math.PI / 2, 0, 0);



        if (isSelected)



        {



            bShape.graphics.lineStyle(1, 0x246318, 0.9, true);



            bShape.graphics.beginGradientFill(



                GradientType.LINEAR,



                [0x42A62C, 0x2D781E],



                [1.0, 1.0],



                [0, 255],



                mat



            );



            bShape.graphics.drawRoundRect(0, 0, w, h, h, h);



            bShape.graphics.endFill();



            badge.addChild(bShape);



            var lblActive:TextField = makeCenteredText("Активно", 10, 0xFFFFFF, w);



            lblActive.y = Math.floor((h - 18) / 2);



            badge.addChild(lblActive);



        }



        else



        {



            bShape.graphics.lineStyle(1, 0xBCCDD8, 0.8, true);



            bShape.graphics.beginGradientFill(



                GradientType.LINEAR,



                [0xF6F9FC, 0xE9F0F6],



                [1.0, 1.0],



                [0, 255],



                mat



            );



            bShape.graphics.drawRoundRect(0, 0, w, h, h, h);



            bShape.graphics.endFill();



            badge.addChild(bShape);



            var lblChoose:TextField = makeCenteredText("Выбрать", 10, 0x4C6982, w);



            lblChoose.y = Math.floor((h - 18) / 2);



            badge.addChild(lblChoose);



        }



    }



    public function applyWwSexMode(modeKey:String):void



    {



        this.mWwSexMode = modeKey;



        this.refreshWwSexModeIndicators();



        ExternalInterface.call("CallGameService", "PostServerCommand", {



            "command": "synapse.set_ww_sex_mode",



            "commandArgs": [modeKey]



        });



    }



    public function refreshWwSexModeIndicators():void



    {



        var groups:Array = this.getModsGroups();



        if (groups.length > 0)



        {



            var opts:Array = groups[0].options as Array;



            if (opts != null)



            {



                for (var i:int = 0; i < opts.length; i++)



                {



                    var k:String = String(opts[i].key);



                    var b:Sprite = this.mModsOptionIndicatorsByKey[k] as Sprite;



                    if (b != null)



                    {



                        this.drawOptionBadge(b, 88, 24, k == this.mWwSexMode);



                    }



                }



            }



        }



    }



    // =========================================================================



    // DISPLAY & NOTIFICATION SECTION & LOGIC



    // =========================================================================



    public function parseDisplayState(packedStr:String):void



    {



        if (packedStr && packedStr != "00" && packedStr != "")



        {



            var pairs:Array = packedStr.split(";");



            for (var i:int = 0; i < pairs.length; i++)



            {



                var pStr:String = String(pairs[i]);



                if (!pStr) continue;



                var kv:Array = pStr.split(":");



                var k:String = String(kv[0]);



                var v:String = String(kv[1]);



                var bVal:Boolean = (v == "1");



                if (k == "th_bal")



                {



                    this.mDisplayFlagsState["thought_balloon"] = bVal;



                }



                else if (k == "th_notif")



                {



                    this.mDisplayFlagsState["thought_notification"] = bVal;



                }



                else if (k == "dir_bal")



                {



                    this.mDisplayFlagsState["direct_balloon"] = bVal;



                }



                else if (k == "dir_notif")



                {



                    this.mDisplayFlagsState["direct_notification"] = bVal;



                }



                else if (k == "dtr_bal")



                {



                    this.mDisplayFlagsState["director_balloon"] = bVal;



                }



                else if (k == "dtr_notif")



                {



                    this.mDisplayFlagsState["director_notification"] = bVal;



                }



            }



        }



    }



    public function buildDisplaySection():void



    {



        this.mDisplayContainer = new Sprite();



        this.mDisplayContainer.visible = false;



        this.mWorkspace.addChild(this.mDisplayContainer);



        var secW:Number = WORKSPACE_W;



        var barH:Number = 28;



        var secY:Number = 0;



        var secBodyH:Number = 430;



        var selfRef:SettingsUI = this;



        this.drawSectionContainerOn(this.mDisplayContainer, secY, secW, barH, secBodyH);



        var secTitle:TextField = makeCenteredText("Настройки отображения баблов и уведомлений", 13, 0xFFFFFF, secW);



        secTitle.x = 0;



        secTitle.y = secY + 4;



        this.mDisplayContainer.addChild(secTitle);



        // Studio Banner Card



        var studioCardH:Number = 38;



        var studioCardY:Number = secY + barH + 6;



        var hintBg:Shape = new Shape();



        var hMat:Matrix = new Matrix();



        hMat.createGradientBox(secW - 24, studioCardH, Math.PI / 2, 0, 0);



        hintBg.graphics.beginGradientFill(



            GradientType.LINEAR,



            [0xECF3FA, 0xDFEAF4],



            [1.0, 1.0],



            [0, 255],



            hMat



        );



        hintBg.graphics.lineStyle(1, 0xB8CBDC, 0.8, true);



        hintBg.graphics.drawRoundRect(12, studioCardY, secW - 24, studioCardH, 6, 6);



        hintBg.graphics.endFill();



        this.mDisplayContainer.addChild(hintBg);



        var studioTitleTf:TextField = makeText("Конструктор баблов (Живой предпросмотр над симом)", 11, 0x19456B);



        studioTitleTf.x = 22;



        studioTitleTf.y = studioCardY + 4;



        this.mDisplayContainer.addChild(studioTitleTf);



        var studioSubTf:TextField = makeText("Интерактивная настройка размеров, положения, шрифтов и анимации в реальном времени.", 10, 0x647B91);



        studioSubTf.x = 22;



        studioSubTf.y = studioCardY + 19;



        this.mDisplayContainer.addChild(studioSubTf);



        var btnOpenStudio:SimsPillButton = new SimsPillButton("Открыть конструктор", 180, 26, "custom_action", "", this, false, 11);



        btnOpenStudio.x = secW - 12 - 188;



        btnOpenStudio.y = studioCardY + 6;



        btnOpenStudio.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.openBalloonStudio();



        });



        this.mDisplayContainer.addChild(btnOpenStudio);



        var scrollW:Number = secW - 24;



        var scrollH:Number = secBodyH - 52;



        this.mDisplayScrollView = new MaxisScrollView(scrollW, scrollH);



        this.mDisplayScrollView.x = 12;



        this.mDisplayScrollView.y = secY + barH + studioCardH + 10;



        this.mDisplayContainer.addChild(this.mDisplayScrollView);



        var bottomCap:Shape = new Shape();



        bottomCap.graphics.beginFill(0xFFFFFF, 1.0);



        bottomCap.graphics.drawRoundRect(1, secY + barH + secBodyH - 8, secW - 2, 7, 4, 4);



        bottomCap.graphics.endFill();



        this.mDisplayContainer.addChild(bottomCap);



    }



    public function reflowDisplayAccordions():void



    {



        var currY:Number = 0;



        var gap:Number = 6;



        for (var i:int = 0; i < this.mDisplayAccordionSections.length; i++)



        {



            var sec:MaxisAccordionSection = this.mDisplayAccordionSections[i] as MaxisAccordionSection;



            if (sec != null)



            {



                sec.y = currY;



                currY += sec.getTotalHeight() + gap;



            }



        }



        if (this.mDisplayScrollView != null)



        {



            this.mDisplayScrollView.updateLayout(currY);



        }



    }



    public function getDisplayGroups():Array



    {



        return [



            {



                "title": "1. ОТОБРАЖЕНИЕ БАБЛОВ И УВЕДОМЛЕНИЙ",



                "items": [



                    {



                        "key": "thought_balloon",



                        "title": "Бабл над головой (мысли персонажа)",



                        "desc": "Показывать облачко с текстом мыслей над головой сима при чтении мыслей и автономии."



                    },



                    {



                        "key": "thought_notification",



                        "title": "Игровое уведомление (мысли персонажа)",



                        "desc": "Показывать всплывающую карточку с текстом мысли и портретом в правом верхнем углу экрана."



                    },



                    {



                        "key": "direct_balloon",



                        "title": "Бабл над головой (живое общение 1-на-1)",



                        "desc": "Показывать речевые баблы с репликами над говорящим персонажем при диалоге."



                    },



                    {



                        "key": "direct_notification",



                        "title": "Игровое уведомление (живое общение 1-на-1)",



                        "desc": "Показывать карточку ответа собеседника с реакцией и портретом в углу экрана."



                    },



                    {



                        "key": "director_balloon",



                        "title": "Бабл над головой (режиссёр фонового общения)",



                        "desc": "Показывать речевые баблы симов во время их фоновых самостоятельных бесед."



                    },



                    {



                        "key": "director_notification",



                        "title": "Игровое уведомление (режиссёр фонового общения)",



                        "desc": "Дублировать реплики симов из автономных бесед во всплывающие уведомления игры."



                    }



                ]



            }



        ];



    }



    public function rebuildDisplayItems():void



    {



        if (!this.mDisplayScrollView) return;



        var prevScroll:Number = this.mDisplayScrollView.getScrollY();



        var scrollContent:Sprite = this.mDisplayScrollView.getContent();



        while (scrollContent.numChildren > 0)



        {



            scrollContent.removeChildAt(0);



        }



        this.mDisplayAccordionSections = [];



        this.mDisplayCheckboxesByKey = {};



        var groups:Array = this.getDisplayGroups();



        var secW:Number = this.mDisplayScrollView.getViewportWidth();



        var selfRef:SettingsUI = this;



        for (var gIdx:int = 0; gIdx < groups.length; gIdx++)



        {



            var grp:Object = groups[gIdx];



            var secTitle:String = String(grp.title);



            var secKey:String = "disp_" + secTitle;



            var isInitiallyExpanded:Boolean = (this.mDisplayExpandedSections[secKey] !== undefined) ?



                Boolean(this.mDisplayExpandedSections[secKey]) : true;



            var accSec:MaxisAccordionSection = new MaxisAccordionSection(



                secTitle,



                secW,



                28,



                isInitiallyExpanded,



                function(tSec:MaxisAccordionSection):void {



                    var k:String = "disp_" + tSec.title;



                    selfRef.mDisplayExpandedSections[k] = tSec.isExpanded;



                    selfRef.reflowDisplayAccordions();



                }



            );



            var grpItems:Array = grp.items as Array;



            if (grpItems != null && grpItems.length > 0)



            {



                this.populateDisplaySectionItems(accSec.content, grpItems, secW, 0);



            }



            scrollContent.addChild(accSec);



            this.mDisplayAccordionSections.push(accSec);



        }



        this.mDisplayScrollView.setOwnerSections(this.mDisplayAccordionSections);



        this.reflowDisplayAccordions();



        if (prevScroll > 0)



        {



            this.mDisplayScrollView.scrollTo(prevScroll);



        }



        else



        {



            this.mDisplayScrollView.resetScroll();



        }



    }



    private function populateDisplaySectionItems(container:Sprite, items:Array, secW:Number, startY:Number = 0):void



    {



        var rowH:Number = 40;



        var selfRef:SettingsUI = this;



        for (var i:int = 0; i < items.length; i++)



        {



            var item:Object = items[i];



            var row:Sprite = new Sprite();



            row.y = startY + i * rowH;



            row.buttonMode = true;



            row.useHandCursor = true;



            row.mouseChildren = true;



            var rowBg:Shape = new Shape();



            rowBg.graphics.beginFill(0xFFFFFF, 0.001);



            rowBg.graphics.drawRect(0, 0, secW, rowH);



            rowBg.graphics.endFill();



            row.addChild(rowBg);



            var sep:Shape = new Shape();



            sep.graphics.lineStyle(1, 0xCBD6E2, 0.40);



            sep.graphics.moveTo(16, rowH - 1);



            sep.graphics.lineTo(secW - 16, rowH - 1);



            row.addChild(sep);



            var titleTf:TextField = makeBoundedText(String(item.title), 12, 0x19456B, secW - 75);



            titleTf.x = 20;



            titleTf.y = 4;



            row.addChild(titleTf);



            var descTf:TextField = makeBoundedText(String(item.desc), 10, 0x647B91, secW - 75);



            descTf.x = 20;



            descTf.y = 20;



            row.addChild(descTf);



            var isFlagOn:Boolean = (this.mDisplayFlagsState[item.key] !== undefined) ?



                Boolean(this.mDisplayFlagsState[item.key]) : true;



            var cb:SimsCheckbox = new SimsCheckbox(String(item.key), isFlagOn, function(k:String, st:Boolean):void {



                selfRef.onDisplayToggleClick(k, st);



            });



            cb.x = secW - 46;



            cb.y = Math.floor((rowH - 20) / 2);



            row.addChild(cb);



            this.mDisplayCheckboxesByKey[item.key] = cb;



            row.addEventListener(MouseEvent.ROLL_OVER, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var rBg:Shape = targetRow.getChildAt(0) as Shape;



                    if (rBg != null)



                    {



                        rBg.graphics.clear();



                        rBg.graphics.beginFill(0x2E80C2, 0.08);



                        rBg.graphics.drawRoundRect(8, 1, secW - 16, rowH - 2, 6, 6);



                        rBg.graphics.endFill();



                    }



                }



            });



            row.addEventListener(MouseEvent.ROLL_OUT, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var rBg:Shape = targetRow.getChildAt(0) as Shape;



                    if (rBg != null)



                    {



                        rBg.graphics.clear();



                        rBg.graphics.beginFill(0xFFFFFF, 0.001);



                        rBg.graphics.drawRect(0, 0, secW, rowH);



                        rBg.graphics.endFill();



                    }



                }



            });



            row.name = String(item.key);



            row.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var flagKey:String = targetRow.name;



                    var rowCb:SimsCheckbox = selfRef.mDisplayCheckboxesByKey[flagKey] as SimsCheckbox;



                    if (rowCb != null)



                    {



                        var curSt:Boolean = rowCb.getState();



                        rowCb.setState(!curSt);



                        selfRef.onDisplayToggleClick(flagKey, !curSt);



                    }



                }



            });



            container.addChild(row);



        }



    }



    public function onDisplayToggleClick(flagKey:String, newState:Boolean):void



    {



        this.mDisplayFlagsState[flagKey] = newState;



        ExternalInterface.call("CallGameService", "PostServerCommand", {



            "command": "synapse.set_display_flag",



            "commandArgs": [flagKey, newState ? "1" : "0"]



        });



    }



    // =========================================================================



    // EXPERIMENTAL SECTION & LOGIC



    // =========================================================================



    public function parseExperimentalState(packedStr:String):void



    {



        if (packedStr && packedStr != "00" && packedStr != "")



        {



            var pairs:Array = packedStr.split(";");



            for (var i:int = 0; i < pairs.length; i++)



            {



                var pStr:String = String(pairs[i]);



                if (!pStr) continue;



                var kv:Array = pStr.split(":");



                var k:String = String(kv[0]);



                var v:String = String(kv[1]);



                var bVal:Boolean = (v == "1");



                if (k == "dyn_act")



                {



                    this.mExperimentalFlagsState["dynamic_interaction_ui_fallback"] = bVal;



                }



                else if (k == "biz")



                {



                    this.mExperimentalFlagsState["home_business_context"] = bVal;



                }



                else if (k == "pause")



                {



                    this.mExperimentalFlagsState["direct_dialogue_pause"] = bVal;



                }



                else if (k == "multisim")



                {



                    this.mExperimentalFlagsState["direct_dialogue_multisim_join"] = bVal;



                }



                else if (k == "alien")



                {



                    this.mExperimentalFlagsState["alien_male_pregnancy"] = bVal;



                }



                else if (k == "insane")



                {



                    this.mExperimentalFlagsState["classic_insane_trait"] = bVal;



                }



                else if (k == "overheard")



                {



                    this.mExperimentalFlagsState["overheard_conversations"] = bVal;



                }



                else if (k == "dossier")



                {



                    this.mExperimentalFlagsState["third_party_dossier"] = bVal;



                }



                else if (k == "trapped")



                {



                    this.mExperimentalFlagsState["trapped_sim_detection"] = bVal;



                }



                else if (k == "last_th")



                {



                    this.mExperimentalFlagsState["last_thought_context"] = bVal;



                }



            }



        }



    }



    // =========================================================================



    // WORLDS / CITIES LORE SECTION



    // =========================================================================



    public function getWorldsList():Array



    {



        return [



            "Виллоу Крик", "Оазис Спрингс", "Ньюкрест", "Гранит Фоллз", "Магнолия Променейд",



            "Винденбург", "Сан Мишуно", "Форготн Холлоу", "Бриндлтон Бэй", "Сельвадорада",



            "Дель-Соль-Вэлли", "Стрейнджервиль", "Сулани", "Глиммербрук", "Волшебный мир",



            "Бритчестер", "Эвергрин-Харбор", "Гора Комореби", "Хэнфорд-он-Бэгли", "Тартоза",



            "Мунвуд Милл", "Коппердейл", "Сан-Секвойя", "Честнат-Ридж", "Томаранг",



            "Сьюдад-Энаморада", "Вранбург", "Батуу", "Сиксим", "Лесная поляна",



            "Забытый грот", "Глухой лес"



        ];



    }



    public function getDefaultWorldDesc(worldKey:String):String



    {



        var map:Object = {



            "Виллоу Крик": "уютный цветущий пригород: тенистые аллеи, плакучие ивы, парки, магнолии и традиционные жилые кварталы с красивыми особняками",



            "Оазис Спрингс": "солнечный пустынный оазис в стиле юго-запада США: пальмы, кактусы, каньоны из красного песчаника, ретро-модерн застройка середины века (Mid-century modern) и сухой знойный климат",



            "Ньюкрест": "просторный тихий пригород с аккуратными лужайками, городским парком и видом на современный скайлайн вдалеке",



            "Магнолия Променейд": "оживленная торговая набережная у залива: бутики, магазины, кирпичные мостовые и уютные прибрежные скверы",



            "Винденбург": "старинный европейский город: фахверковые дома в стиле Тюдоров, булыжные мостовые, древние руины на утесах, ветряные мельницы, живописные фьорды и бурная клубная жизнь",



            "Сан Мишуно": "шумный интернациональный мегаполис: высотные небоскребы, пентхаусы, тесные квартиры, блошиные рынки, уличная еда со всего мира, фестивали и яркие граффити",



            "Форготн Холлоу": "мрачный готический туманный анклав: вечные сумерки, старинные склепы, викторианские поместья, сухие корявые деревья, чеснок и древние вампиры",



            "Бриндлтон Бэй": "уютный прибрежный портовый городок Новой Англии: маяк, деревянные коттеджи у моря, песчаные пляжи, туманы, соленый морской бриз и культ домашних питомцев (кошек и собак)",



            "Сельвадорада": "латиноамериканский тропический край: густые непроходимые джунгли, древние храмы и руины цивилизации омисканцев, бурные реки, водопады и колоритный рынок с местной культурой",



            "Дель-Соль-Вэлли": "гламурный аналог Лос-Анджелеса и Голливуда: пальмовые бульвары, аллея славы, киностудии, роскошные особняки знаменитостей на холмах Пиннаклс и палящее калифорнийское солнце",



            "Стрейнджервиль": "загадочный военный городок в каньонах пустыни: секретная лаборатория, бункеры, параноидальные заговоры, причудливая флора и аномальная атмосфера тайн в стиле Зоны 51",



            "Сулани": "райский тропический полинезийский архипелаг: бирюзовые лагуны с кораллами, действующий вулкан, песчаные пляжи, бунгало на сваях, культура кавы и духи предков",



            "Глиммербрук": "уединенный сказочный лесной поселок: густые сосны, бурлящий водопад, каменистая река, деревянные шале и скрытый таинственный портал в Волшебный мир",



            "Волшебный мир": "парящие в космической пустоте магические острова: сиренево-звездное небо, Аллея Заклинателей, древний замок магии, парящие скалы и чистая колдовская энергия",



            "Бритчестер": "величественный английский университетский городок: старинный неоготический Университет Бритчестера, ультрасовременный Институт Фоксбери, каналы, пабы и студенческая академическая жизнь",



            "Эвергрин-Харбор": "бывший промышленный тихоокеанский порт: переоборудованные фабрики, контейнерное жилье, экологические проекты, смоговые дымки или кристально чистая зеленая гавань",



            "Гора Комореби": "живописный японский горный курорт: заснеженные вершины для лыж и сноуборда, горячие источники (онсэны), бамбуковые рощи, синтоистские святилища и цветущая сакура",



            "Хэнфорд-он-Бэгли": "пасторальная английская сельская глубинка: каменные коттеджи с соломенными крышами, зеленые холмы, пастбища коров и лам, дикие лисы, птицы, кролики и уютная деревенская ярмарка",



            "Тартоза": "романтическое средиземноморское побережье: водопады любви, оливковые и цитрусовые рощи, бирюзовые морские бухты, итальянская архитектура и идеальная атмосфера для свадеб",



            "Мунвуд Милл": "заброшенный лесопильный поселок в темных хвойных лесах: ржавые станки, индустриальные руины, полнолуние над озером Лунвуд, подземные тоннели и логова стай оборотней",



            "Коппердейл": "уютный шахтерский городок у озера в духе американского Северо-Запада: старшая школа, парк аттракционов с колесом обозрения на пирсе, чайный магазин боба и подростковая драма",



            "Сан-Секвойя": "спокойный калифорнийский залив в стиле залива Сан-Франциско: грандиозный мост, набережные, пригородные семейные дома, парки у воды и общественный центр",



            "Честнат-Ридж": "просторные прерии американского Дикого Запада: каньоны, ранчо, поля для верховой езды, загоны для лошадей, нектарные погреба и ковбойский колорит",



            "Томаранг": "колоритный край Юго-Восточной Азии: густые тропики, ночной рынок с запахами специй, арендные жилые комплексы, ботанический заповедник и старинные буддийские храмы",



            "Сьюдад-Энаморада": "страстный южноамериканский романтический мегаполис: архитектура в стиле Мехико, роскошные зеленые парки свиданий, мотели на час, бары на крышах и стена влюбленных",



            "Вранбург": "мистический викторианский край потустороннего мира: склепы, старинные кладбища, блуждающие призраки, вороны, колокольня Смерти и мрачный загробный колорит",



            "Батуу": "далекая застава на краю Галактики Звёздных Войн: каменные шпили аванпоста Черный Шпиль, дроиды, кантина Оги, космические корабли, Сопротивление и Первый Орден",



            "Гранит Фоллз": "дремучий хвойный национальный заповедник: вековые сосны, скалы, палаточные кемпинги, костры, сбор трав и скрытое жилище лесного отшельника",



            "Сиксим": "чужеродная внеземная планета: светящиеся неоновые кристаллы, инопланетные растения, низкая гравитация, парящие споры и странные атмосферные явления",



            "Лесная поляна": "тайная сказочная поляна: волшебное дерево, розово-голубое свечение, мерцающие водопады, светлячки и редкие цветы",



            "Забытый грот": "скрытая глубокая пещера в каньоне: сталактиты, кристаллы, светящиеся пещерные мхи, подземное озеро и редкие ископаемые",



            "Глухой лес": "глухая непроходимая чаща заповедника: вековые деревья, заросшие тропы, дикая природа и бревенчатая хижина отшельника"



        };



        if (map[worldKey] !== undefined)



        {



            return String(map[worldKey]);



        }



        return "";



    }



    public function parseWorldLoreState(rawStr:String):void



    {



        if (!rawStr || rawStr == "00" || rawStr == "") return;



        var parts:Array = rawStr.split("|");



        if (parts.length >= 1)



        {



            var curW:String = this.decodeSafeStr(parts[0]);



            if (curW && curW != "")



            {



                this.mActiveLotWorldKey = curW;



                if (!this.mCurrentWorldKey || this.mCurrentWorldKey == "")



                {



                    this.mCurrentWorldKey = curW;



                }



            }



        }



        this.mCustomWorldData = {};



        if (parts.length >= 3)



        {



            for (var i:int = 2; i < parts.length; i++)



            {



                var entryStr:String = parts[i];



                if (!entryStr) continue;



                var subParts:Array = entryStr.split(":");



                if (subParts.length >= 3)



                {



                    var wKey:String = this.decodeSafeStr(subParts[0]);



                    var wName:String = this.decodeSafeStr(subParts[1]);



                    var wDesc:String = this.decodeSafeStr(subParts[2]);



                    this.mCustomWorldData[wKey] = {



                        "name": wName,



                        "desc": wDesc



                    };



                }



            }



        }



    }



    public function onWorldSavedCommand(args:Array):void



    {



        var savedKey:String = (args && args.length > 1) ? this.decodeSafeStr(String(args[1])) : this.mCurrentWorldKey;



        if (this.mWorldSavedBadge)



        {



            this.mWorldSavedBadge.text = "Сохранено в это сохранение!";



            this.mWorldSavedBadge.visible = true;



            var selfRef:SettingsUI = this;



            setTimeout(function():void {



                if (selfRef.mWorldSavedBadge) selfRef.mWorldSavedBadge.visible = false;



            }, 2500);



        }



        if (this.mWorldStatusLabel)



        {



            this.mWorldStatusLabel.text = "Кастомное описание (это сохранение)";



        }



        this.rebuildWorldButtons();



    }



    public function onWorldClearedCommand(args:Array):void



    {



        var clearedKey:String = (args && args.length > 1) ? this.decodeSafeStr(String(args[1])) : this.mCurrentWorldKey;



        if (this.mCustomWorldData && clearedKey)



        {



            delete this.mCustomWorldData[clearedKey];



        }



        if (this.mWorldSavedBadge)



        {



            this.mWorldSavedBadge.text = "Сброшено к стандартному!";



            this.mWorldSavedBadge.visible = true;



            var selfRef:SettingsUI = this;



            setTimeout(function():void {



                if (selfRef.mWorldSavedBadge) selfRef.mWorldSavedBadge.visible = false;



            }, 2500);



        }



        if (this.mWorldStatusLabel)



        {



            this.mWorldStatusLabel.text = "Стандартное описание игры/мода";



        }



        if (this.mWorldCustomNameInput) this.mWorldCustomNameInput.text = "";



        if (this.mWorldDescInput) this.mWorldDescInput.text = this.getDefaultWorldDesc(this.mCurrentWorldKey);



        this.updateWorldCounter();



        this.rebuildWorldButtons();



    }



    public function buildWorldsSection():void



    {



        this.mWorldsContainer = new Sprite();



        this.mWorldsContainer.visible = false;



        this.mWorkspace.addChild(this.mWorldsContainer);



        var secW:Number = WORKSPACE_W;



        var barH:Number = 28;



        var secY:Number = 0;



        var secBodyH:Number = 430;



        var selfRef:SettingsUI = this;



        this.drawSectionContainerOn(this.mWorldsContainer, secY, secW, barH, secBodyH);



        var secTitle:TextField = makeCenteredText("Описания городов и миров (для ИИ)", 13, 0xFFFFFF, secW);



        secTitle.x = 0;



        secTitle.y = secY + 4;



        this.mWorldsContainer.addChild(secTitle);



        var hintBg:Shape = new Shape();



        var hMat:Matrix = new Matrix();



        hMat.createGradientBox(secW - 24, 26, Math.PI / 2, 0, 0);



        hintBg.graphics.beginGradientFill(



            GradientType.LINEAR,



            [0xECF3FA, 0xDFEAF4],



            [1.0, 1.0],



            [0, 255],



            hMat



        );



        hintBg.graphics.lineStyle(1, 0xB8CBDC, 0.8, true);



        hintBg.graphics.drawRoundRect(12, secY + barH + 6, secW - 24, 26, 6, 6);



        this.mWorldsContainer.addChild(hintBg);



        var hintTf:TextField = makeText("Настройте атмосферу каждого города. Описания сохраняются индивидуально для каждого сохранения.", 11, 0x1E466B);



        hintTf.x = 22;



        hintTf.y = secY + barH + 11;



        this.mWorldsContainer.addChild(hintTf);



        // LEFT PANEL: World list (width = 208, height = 354)



        var lpX:Number = 12;



        var lpY:Number = secY + barH + 38;



        var lpW:Number = 208;



        var lpH:Number = 354;



        var lpBg:Shape = new Shape();



        lpBg.graphics.beginFill(0xF5F8FB, 0.95);



        lpBg.graphics.lineStyle(1, 0xCBD6E2, 1.0);



        lpBg.graphics.drawRoundRect(lpX, lpY, lpW, lpH, 6, 6);



        lpBg.graphics.endFill();



        this.mWorldsContainer.addChild(lpBg);



        var lpHeaderBg:Shape = new Shape();



        lpHeaderBg.graphics.beginFill(0xDFE8F2, 1.0);



        lpHeaderBg.graphics.drawRoundRect(lpX, lpY, lpW, 26, 6, 6);



        lpHeaderBg.graphics.endFill();



        this.mWorldsContainer.addChild(lpHeaderBg);



        var lpTitle:TextField = makeCenteredText("СПИСОК ГОРОДОВ", 11, 0x19456B, lpW);



        lpTitle.x = lpX;



        lpTitle.y = lpY + 5;



        this.mWorldsContainer.addChild(lpTitle);



        this.mWorldsScrollView = new MaxisScrollView(lpW - 4, lpH - 30);



        this.mWorldsScrollView.x = lpX + 2;



        this.mWorldsScrollView.y = lpY + 28;



        this.mWorldsContainer.addChild(this.mWorldsScrollView);



        this.mWorldButtonsContainer = this.mWorldsScrollView.getContent();



        // RIGHT PANEL: Editor (width = 444, height = 354)



        var rpX:Number = lpX + lpW + 6;



        var rpY:Number = lpY;



        var rpW:Number = secW - rpX - 12;



        var rpH:Number = lpH;



        var rpBg:Shape = new Shape();



        rpBg.graphics.beginFill(0xFFFFFF, 0.95);



        rpBg.graphics.lineStyle(1, 0xCBD6E2, 1.0);



        rpBg.graphics.drawRoundRect(rpX, rpY, rpW, rpH, 6, 6);



        rpBg.graphics.endFill();



        this.mWorldsContainer.addChild(rpBg);



        this.mWorldTitleLabel = makeText("Город: ...", 13, 0x19456B);



        this.mWorldTitleLabel.x = rpX + 14;



        this.mWorldTitleLabel.y = rpY + 8;



        this.mWorldsContainer.addChild(this.mWorldTitleLabel);



        this.mWorldStatusLabel = makeText("Стандартное описание игры/мода", 10, 0x647B91);



        this.mWorldStatusLabel.x = rpX + 14;



        this.mWorldStatusLabel.y = rpY + 27;



        this.mWorldsContainer.addChild(this.mWorldStatusLabel);



        // Custom name input



        var nameLbl:TextField = makeText("Пользовательское название (если город переименован):", 10, 0x647B91);



        nameLbl.x = rpX + 14;



        nameLbl.y = rpY + 45;



        this.mWorldsContainer.addChild(nameLbl);



        var nameBg:Shape = new Shape();



        nameBg.graphics.beginFill(0xF8FAFC, 1.0);



        nameBg.graphics.lineStyle(1, 0xB8CBDC, 1.0);



        nameBg.graphics.drawRoundRect(rpX + 14, rpY + 62, rpW - 28, 24, 4, 4);



        nameBg.graphics.endFill();



        this.mWorldsContainer.addChild(nameBg);



        this.mWorldCustomNameInput = new TextField();



        this.mWorldCustomNameInput.type = "input";



        this.mWorldCustomNameInput.embedFonts = true;



        this.mWorldCustomNameInput.selectable = true;



        this.mWorldCustomNameInput.mouseEnabled = true;



        this.mWorldCustomNameInput.multiline = false;



        this.mWorldCustomNameInput.x = rpX + 18;



        this.mWorldCustomNameInput.y = rpY + 65;



        this.mWorldCustomNameInput.width = rpW - 36;



        this.mWorldCustomNameInput.height = 20;



        var nameFmt:TextFormat = new TextFormat("$TextFont", 11, COL_LABEL_DARK, false);



        this.mWorldCustomNameInput.defaultTextFormat = nameFmt;



        this.mWorldCustomNameInput.setTextFormat(nameFmt);



        this.mWorldCustomNameInput.maxChars = 60;



        this.mWorldsContainer.addChild(this.mWorldCustomNameInput);



        this.mWorldCustomNameInput.addEventListener(FocusEvent.FOCUS_IN, function(e:FocusEvent):void {



            try {



                var cmFi1:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cmFi1.CallGameService("SetTextFieldInput", true);



            } catch(eFi1:Error) {}



        });



        this.mWorldCustomNameInput.addEventListener(FocusEvent.FOCUS_OUT, function(e:FocusEvent):void {



            try {



                var cmFo1:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cmFo1.CallGameService("SetTextFieldInput", false);



            } catch(eFo1:Error) {}



        });



        this.mWorldCustomNameInput.addEventListener(Event.CHANGE, function(e:Event):void {



            selfRef.mWorldCustomNameInput.defaultTextFormat = nameFmt;



            if (selfRef.mWorldSavedBadge) {



                selfRef.mWorldSavedBadge.visible = false;



            }



        });



        // Description multiline input



        var descLbl:TextField = makeText("Описание атмосферы и окружения для мыслей и диалогов ИИ:", 10, 0x647B91);



        descLbl.x = rpX + 14;



        descLbl.y = rpY + 92;



        this.mWorldsContainer.addChild(descLbl);



        var descBg:Shape = new Shape();



        descBg.graphics.beginFill(0xF8FAFC, 1.0);



        descBg.graphics.lineStyle(1, 0xB8CBDC, 1.0);



        descBg.graphics.drawRoundRect(rpX + 14, rpY + 110, rpW - 28, 170, 4, 4);



        descBg.graphics.endFill();



        this.mWorldsContainer.addChild(descBg);



        this.mWorldDescInput = new TextField();



        this.mWorldDescInput.type = "input";



        this.mWorldDescInput.embedFonts = true;



        this.mWorldDescInput.selectable = true;



        this.mWorldDescInput.mouseEnabled = true;



        this.mWorldDescInput.multiline = true;



        this.mWorldDescInput.wordWrap = true;



        this.mWorldDescInput.x = rpX + 18;



        this.mWorldDescInput.y = rpY + 114;



        this.mWorldDescInput.width = rpW - 36;



        this.mWorldDescInput.height = 162;



        var descFmt:TextFormat = new TextFormat("$TextFont", 11, COL_LABEL_DARK, false);



        descFmt.leading = 3;



        this.mWorldDescInput.defaultTextFormat = descFmt;



        this.mWorldDescInput.setTextFormat(descFmt);



        this.mWorldDescInput.maxChars = 2000;



        this.mWorldsContainer.addChild(this.mWorldDescInput);



        this.mWorldDescInput.addEventListener(FocusEvent.FOCUS_IN, function(e:FocusEvent):void {



            try {



                var cmFi2:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cmFi2.CallGameService("SetTextFieldInput", true);



            } catch(eFi2:Error) {}



        });



        this.mWorldDescInput.addEventListener(FocusEvent.FOCUS_OUT, function(e:FocusEvent):void {



            try {



                var cmFo2:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cmFo2.CallGameService("SetTextFieldInput", false);



            } catch(eFo2:Error) {}



        });



        this.mWorldDescInput.addEventListener(Event.CHANGE, function(e:Event):void {



            selfRef.mWorldDescInput.defaultTextFormat = descFmt;



            selfRef.updateWorldCounter();



            if (selfRef.mWorldSavedBadge) {



                selfRef.mWorldSavedBadge.visible = false;



            }



        });



        this.mWorldCounter = makeText("Символов: 0 / 2000", 10, 0x7E94A6);



        this.mWorldCounter.x = rpX + 14;



        this.mWorldCounter.y = rpY + 286;



        this.mWorldsContainer.addChild(this.mWorldCounter);



        this.mWorldSavedBadge = makeText("Сохранено в это сохранение!", 11, 0x2A7E3B);



        this.mWorldSavedBadge.x = rpX + 160;



        this.mWorldSavedBadge.y = rpY + 285;



        this.mWorldSavedBadge.visible = false;



        this.mWorldsContainer.addChild(this.mWorldSavedBadge);



        // 4 Action Buttons Row at bottom of right panel



        var btnY:Number = rpY + 314;



        var btnClear:SimsPillButton = new SimsPillButton("Очистить", 88, 28, "custom_action", "", this, false, 11);



        btnClear.x = rpX + 14;



        btnClear.y = btnY;



        btnClear.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.clearCurrentWorldLore();



        });



        this.mWorldsContainer.addChild(btnClear);



        var btnReset:SimsPillButton = new SimsPillButton("По умолчанию", 114, 28, "custom_action", "", this, false, 11);



        btnReset.x = btnClear.x + 88 + 8;



        btnReset.y = btnY;



        btnReset.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.resetCurrentWorldLore();



        });



        this.mWorldsContainer.addChild(btnReset);



        var btnDelete:SimsPillButton = new SimsPillButton("Сбросить", 90, 28, "custom_action", "", this, false, 11);



        btnDelete.x = btnReset.x + 114 + 8;



        btnDelete.y = btnY;



        btnDelete.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.deleteCustomWorldLore();



        });



        this.mWorldsContainer.addChild(btnDelete);



        var btnSave:SimsPillButton = new SimsPillButton("Сохранить", 104, 28, "custom_action", "", this, false, 11);



        btnSave.x = btnDelete.x + 90 + 8;



        btnSave.y = btnY;



        btnSave.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.saveCurrentWorldLore();



        });



        this.mWorldsContainer.addChild(btnSave);



        // Initial selection



        this.selectWorld(this.mCurrentWorldKey || this.mActiveLotWorldKey || "Виллоу Крик");



    }



    public function updateWorldCounter():void



    {



        if (!this.mWorldCounter || !this.mWorldDescInput) return;



        var len:int = this.mWorldDescInput.text ? this.mWorldDescInput.text.length : 0;



        this.mWorldCounter.text = "Символов: " + len + " / 2000";



    }



    public function rebuildWorldButtons():void



    {



        if (!this.mWorldButtonsContainer) return;



        while (this.mWorldButtonsContainer.numChildren > 0)



        {



            this.mWorldButtonsContainer.removeChildAt(0);



        }



        this.mWorldButtons = [];



        var list:Array = this.getWorldsList();



        var btnW:Number = 186;



        var btnH:Number = 26;



        var gap:Number = 2;



        var selfRef:SettingsUI = this;



        for (var i:int = 0; i < list.length; i++)



        {



            var wName:String = String(list[i]);



            var isCurrentSel:Boolean = (wName == this.mCurrentWorldKey);



            var isActiveLot:Boolean = (wName == this.mActiveLotWorldKey);



            var isCustom:Boolean = Boolean(this.mCustomWorldData && this.mCustomWorldData[wName]);



            var row:Sprite = new Sprite();



            row.x = 2;



            row.y = i * (btnH + gap);



            row.buttonMode = true;



            row.useHandCursor = true;



            row.mouseChildren = false;



            var bg:Shape = new Shape();



            if (isCurrentSel)



            {



                bg.graphics.beginFill(0x2D72B0, 1.0);



                bg.graphics.drawRoundRect(0, 0, btnW, btnH, 4, 4);



                bg.graphics.endFill();



            }



            else



            {



                bg.graphics.beginFill(0xFFFFFF, 0.85);



                bg.graphics.lineStyle(1, 0xCBD6E2, 0.8);



                bg.graphics.drawRoundRect(0, 0, btnW, btnH, 4, 4);



                bg.graphics.endFill();



            }



            row.addChild(bg);



            var labelColor:uint = isCurrentSel ? 0xFFFFFF : (isActiveLot ? 0x1E598A : 0x19456B);



            var dispText:String = wName;



            if (isActiveLot)



            {



                dispText += " [текущий]";



            }



            if (isCustom)



            {



                dispText += " *";



            }



            var tf:TextField = makeText(dispText, 11, labelColor);



            tf.x = 8;



            tf.y = 4;



            tf.mouseEnabled = false;



            row.addChild(tf);



            (function(key:String, spr:Sprite, isSel:Boolean):void {



                spr.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



                    selfRef.selectWorld(key);



                });



                if (!isSel)



                {



                    spr.addEventListener(MouseEvent.ROLL_OVER, function(e:MouseEvent):void {



                        spr.alpha = 0.85;



                    });



                    spr.addEventListener(MouseEvent.ROLL_OUT, function(e:MouseEvent):void {



                        spr.alpha = 1.0;



                    });



                }



            })(wName, row, isCurrentSel);



            this.mWorldButtonsContainer.addChild(row);



            this.mWorldButtons.push(row);



        }



        var totalH:Number = list.length * (btnH + gap);



        if (this.mWorldsScrollView != null)



        {



            this.mWorldsScrollView.updateLayout(totalH);



        }



    }



    public function selectWorld(worldKey:String):void



    {



        if (!worldKey) return;



        this.mCurrentWorldKey = worldKey;



        if (this.mWorldSavedBadge) this.mWorldSavedBadge.visible = false;



        var customObj:Object = (this.mCustomWorldData && this.mCustomWorldData[worldKey]) ? this.mCustomWorldData[worldKey] : null;



        var hasCustom:Boolean = (customObj != null && (customObj.desc != "" || customObj.name != ""));



        if (this.mWorldTitleLabel)



        {



            var titleStr:String = "Город: " + worldKey;



            if (worldKey == this.mActiveLotWorldKey)



            {



                titleStr += " [активный участок]";



            }



            this.mWorldTitleLabel.text = titleStr;



        }



        if (this.mWorldStatusLabel)



        {



            this.mWorldStatusLabel.text = hasCustom ? "Кастомное описание (это сохранение)" : "Стандартное описание игры/мода";



        }



        if (this.mWorldCustomNameInput)



        {



            this.mWorldCustomNameInput.text = (hasCustom && customObj.name) ? String(customObj.name) : "";



            var nf:TextFormat = new TextFormat("$TextFont", 11, COL_LABEL_DARK, false);



            this.mWorldCustomNameInput.defaultTextFormat = nf;



            this.mWorldCustomNameInput.setTextFormat(nf);



        }



        if (this.mWorldDescInput)



        {



            if (hasCustom && customObj.desc)



            {



                this.mWorldDescInput.text = String(customObj.desc);



            }



            else



            {



                this.mWorldDescInput.text = this.getDefaultWorldDesc(worldKey);



            }



            var df:TextFormat = new TextFormat("$TextFont", 11, COL_LABEL_DARK, false);



            df.leading = 3;



            this.mWorldDescInput.defaultTextFormat = df;



            this.mWorldDescInput.setTextFormat(df);



        }



        this.updateWorldCounter();



        this.rebuildWorldButtons();



    }



    public function clearCurrentWorldLore():void



    {



        if (this.mWorldCustomNameInput) this.mWorldCustomNameInput.text = "";



        if (this.mWorldDescInput) this.mWorldDescInput.text = "";



        this.updateWorldCounter();



        if (stage && this.mWorldDescInput)



        {



            stage.focus = this.mWorldDescInput;



            try {



                var cm:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cm.CallGameService("SetTextFieldInput", true);



            } catch(eClr:Error) {}



        }



    }



    public function resetCurrentWorldLore():void



    {



        if (!this.mCurrentWorldKey) return;



        if (this.mWorldCustomNameInput) this.mWorldCustomNameInput.text = "";



        var defDesc:String = this.getDefaultWorldDesc(this.mCurrentWorldKey);



        if (this.mWorldDescInput)



        {



            this.mWorldDescInput.text = defDesc;



            var df:TextFormat = new TextFormat("$TextFont", 11, COL_LABEL_DARK, false);



            df.leading = 3;



            this.mWorldDescInput.defaultTextFormat = df;



            this.mWorldDescInput.setTextFormat(df);



        }



        this.updateWorldCounter();



    }



    public function deleteCustomWorldLore():void



    {



        if (!this.mCurrentWorldKey) return;



        var encKey:String = this.encodeSafeStr(this.mCurrentWorldKey);



        ExternalInterface.call("CallGameService", "PostServerCommand", {



            "command": "synapse.delete_world_lore",



            "commandArgs": [encKey]



        });



        if (this.mCustomWorldData)



        {



            delete this.mCustomWorldData[this.mCurrentWorldKey];



        }



        if (this.mWorldCustomNameInput) this.mWorldCustomNameInput.text = "";



        var defDesc:String = this.getDefaultWorldDesc(this.mCurrentWorldKey);



        if (this.mWorldDescInput)



        {



            this.mWorldDescInput.text = defDesc;



            var df:TextFormat = new TextFormat("$TextFont", 11, COL_LABEL_DARK, false);



            df.leading = 3;



            this.mWorldDescInput.defaultTextFormat = df;



            this.mWorldDescInput.setTextFormat(df);



        }



        if (this.mWorldSavedBadge)



        {



            this.mWorldSavedBadge.text = "Сброшено к стандартному!";



            this.mWorldSavedBadge.visible = true;



            var selfRef:SettingsUI = this;



            setTimeout(function():void {



                if (selfRef.mWorldSavedBadge) selfRef.mWorldSavedBadge.visible = false;



            }, 2500);



        }



        if (this.mWorldStatusLabel)



        {



            this.mWorldStatusLabel.text = "Стандартное описание игры/мода";



        }



        this.updateWorldCounter();



        this.rebuildWorldButtons();



    }



    public function saveCurrentWorldLore():void



    {



        if (!this.mCurrentWorldKey) return;



        var customName:String = (this.mWorldCustomNameInput) ? this.mWorldCustomNameInput.text : "";



        var customDesc:String = (this.mWorldDescInput) ? this.mWorldDescInput.text : "";



        var defDesc:String = this.getDefaultWorldDesc(this.mCurrentWorldKey);



        var encKey:String = this.encodeSafeStr(this.mCurrentWorldKey);



        var encName:String = this.encodeSafeStr(customName);



        var encDesc:String = this.encodeSafeStr(customDesc);



        ExternalInterface.call("CallGameService", "PostServerCommand", {



            "command": "synapse.set_world_lore",



            "commandArgs": [encKey, encName, encDesc]



        });



        if (!this.mCustomWorldData) this.mCustomWorldData = {};



        this.mCustomWorldData[this.mCurrentWorldKey] = {



            "name": customName,



            "desc": customDesc



        };



        if (this.mWorldSavedBadge)



        {



            this.mWorldSavedBadge.text = "Сохранено в это сохранение!";



            this.mWorldSavedBadge.visible = true;



            var selfRef:SettingsUI = this;



            setTimeout(function():void {



                if (selfRef.mWorldSavedBadge) selfRef.mWorldSavedBadge.visible = false;



            }, 2500);



        }



        if (this.mWorldStatusLabel)



        {



            var isCustom:Boolean = (customName != "" || (customDesc != "" && customDesc != defDesc));



            this.mWorldStatusLabel.text = isCustom ? "Кастомное описание (это сохранение)" : "Стандартное описание игры/мода";



        }



        this.rebuildWorldButtons();



    }



    // =========================================================================



    // AUTONOMOUS DIRECTOR SECTION & LOGIC (RADIO-STATION STYLE)



    // =========================================================================



    public function parseDirectorState(packedStr:String):void



    {



        if (!packedStr || packedStr == "00" || packedStr == "") return;



        var parts:Array = packedStr.split("|");



        for (var i:int = 0; i < parts.length; i++)



        {



            var p:String = String(parts[i]);



            if (p.indexOf("en:") == 0)



            {



                this.mDirectorEnabled = (p.substr(3) == "1");



            }



            else if (p.indexOf("dis:") == 0)



            {



                var disStr:String = p.substr(4);



                this.mDirectorDisabledTriggers = {};



                if (disStr != "none" && disStr != "")



                {



                    var disKeys:Array = disStr.split(",");



                    for (var j:int = 0; j < disKeys.length; j++)



                    {



                        var k:String = String(disKeys[j]);



                        if (k && k != "")



                        {



                            this.mDirectorDisabledTriggers[k] = true;



                        }



                    }



                }



            }



            else if (p.indexOf("simp:") == 0)
            {
                var simpStr:String = p.substr(5);
                var simpArr:Array = simpStr.split(",");
                if (simpArr.length >= 5)
                {
                    this.mSimplifiedEnabled = (simpArr[0] == "1");
                    this.mSimplifiedSilenceSec = parseInt(simpArr[1]) || 180;
                    this.mSimplifiedChancePct = parseInt(simpArr[2]) || 40;
                    this.mSimplifiedBalloon = (simpArr[3] == "1");
                    this.mSimplifiedNotif = (simpArr[4] == "1");
                }
            }
            else if (p.indexOf("tm:") == 0)



            {



                var tmStr:String = p.substr(3);



                var tmArr:Array = tmStr.split(",");



                if (tmArr.length >= 3)



                {



                    this.mDirectorSilenceSec = parseInt(tmArr[0]) || 240;



                    this.mDirectorPairSec = parseInt(tmArr[1]) || 450;



                    this.mDirectorGraceSec = parseInt(tmArr[2]) || 60;



                }



            }



            else if (p.indexOf("ovr:") == 0)



            {



                var ovrStr:String = p.substr(4);



                this.mDirectorOverrides = {};



                if (ovrStr != "none" && ovrStr != "")



                {



                    var ovrItems:Array = ovrStr.split(",");



                    for (var ovIdx:int = 0; ovIdx < ovrItems.length; ovIdx++)



                    {



                        var rawOvr:String = String(ovrItems[ovIdx]);



                        var ovParts:Array = rawOvr.split(":");
                        if (ovParts.length >= 3)
                        {
                            var oKey:String = String(ovParts[0]);
                            var oImm:Boolean = (ovParts[1] == "1");
                            var oPrio:int = parseInt(ovParts[2]) || 50;
                            var oPrompt:String = (ovParts.length >= 4 && String(ovParts[3]) != "00") ? this.decodeSafeStr(String(ovParts[3])) : "";
                            var oAnim:Boolean = (ovParts.length >= 5) ? (ovParts[4] == "1") : true;
                            var oType:String = (ovParts.length >= 6 && String(ovParts[5]) != "") ? String(ovParts[5]) : "AUTO";
                            this.mDirectorOverrides[oKey] = {
                                immediate: oImm,
                                priority: oPrio,
                                custom_prompt: oPrompt,
                                enable_anim: oAnim,
                                anim_type: oType
                            };



                        }



                    }



                }



            }



        }



    }



    public function buildDirectorSection():void



    {



        this.mDirectorContainer = new Sprite();



        this.mDirectorContainer.visible = false;



        this.mWorkspace.addChild(this.mDirectorContainer);



        var secW:Number = WORKSPACE_W;



        var barH:Number = 28;



        var secY:Number = 0;



        var secBodyH:Number = 430;



        var selfRef:SettingsUI = this;



        this.drawSectionContainerOn(this.mDirectorContainer, secY, secW, barH, secBodyH);



        var secTitle:TextField = makeCenteredText("Режиссёр живого общения (Автономные сценарии)", 13, 0xFFFFFF, secW);



        secTitle.x = 0;



        secTitle.y = secY + 4;



        this.mDirectorContainer.addChild(secTitle);



        // TOP BANNER: Master switch



        var topBannerH:Number = 34;



        var topBannerY:Number = secY + barH + 6;



        var hintBg:Shape = new Shape();



        var hMat:Matrix = new Matrix();



        hMat.createGradientBox(secW - 24, topBannerH, Math.PI / 2, 0, 0);



        hintBg.graphics.beginGradientFill(



            GradientType.LINEAR,



            [0xECF3FA, 0xDFEAF4],



            [1.0, 1.0],



            [0, 255],



            hMat



        );



        hintBg.graphics.lineStyle(1, 0xB8CBDC, 0.8, true);



        hintBg.graphics.drawRoundRect(12, topBannerY, secW - 24, topBannerH, 6, 6);



        this.mDirectorContainer.addChild(hintBg);



        this.mDirectorMasterCheckbox = new SimsCheckbox("director_master", this.mDirectorEnabled, function(k:String, st:Boolean):void {



            selfRef.onDirectorMasterToggle(st);



        });



        this.mDirectorMasterCheckbox.x = 22;



        this.mDirectorMasterCheckbox.y = topBannerY + 7;



        this.mDirectorContainer.addChild(this.mDirectorMasterCheckbox);



        var masterTitleTf:TextField = makeText("Включить режиссёра живого общения", 12, 0x19456B);



        masterTitleTf.x = 48;



        masterTitleTf.y = topBannerY + 3;



        this.mDirectorContainer.addChild(masterTitleTf);



        var masterHintTf:TextField = makeText("ИИ автономно оценивает обстановку и запускает живые диалоги персонажей", 10, 0x647B91);



        masterHintTf.x = 48;



        masterHintTf.y = topBannerY + 18;



        this.mDirectorContainer.addChild(masterHintTf);



        var btnDirectorTimers:SimsPillButton = new SimsPillButton("Настройка времени", 146, 24, "custom_action", "", this, false, 11);



        btnDirectorTimers.x = secW - 12 - 150;



        btnDirectorTimers.y = topBannerY + 5;



        btnDirectorTimers.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.showDirectorTimersModal();



        });



        this.mDirectorContainer.addChild(btnDirectorTimers);



        // LEFT PANEL: Location list (width = 208, height = 356)



        var lpX:Number = 12;



        var lpY:Number = topBannerY + topBannerH + 6;



        var lpW:Number = 208;



        var lpH:Number = 356;



        var lpBg:Shape = new Shape();



        lpBg.graphics.beginFill(0xF5F8FB, 0.95);



        lpBg.graphics.lineStyle(1, 0xCBD6E2, 1.0);



        lpBg.graphics.drawRoundRect(lpX, lpY, lpW, lpH, 6, 6);



        lpBg.graphics.endFill();



        this.mDirectorContainer.addChild(lpBg);



        var lpHeaderBg:Shape = new Shape();



        lpHeaderBg.graphics.beginFill(0xDFE8F2, 1.0);



        lpHeaderBg.graphics.drawRoundRect(lpX, lpY, lpW, 26, 6, 6);



        lpHeaderBg.graphics.endFill();



        this.mDirectorContainer.addChild(lpHeaderBg);



        var lpTitle:TextField = makeCenteredText("МЕСТА ДЕЙСТВИЯ", 11, 0x19456B, lpW);



        lpTitle.x = lpX;



        lpTitle.y = lpY + 5;



        this.mDirectorContainer.addChild(lpTitle);



        this.mDirectorStateButtonsContainer = new Sprite();



        this.mDirectorStateButtonsContainer.x = lpX + 6;



        this.mDirectorStateButtonsContainer.y = lpY + 32;



        this.mDirectorContainer.addChild(this.mDirectorStateButtonsContainer);



        // RIGHT PANEL: Scenarios List (width = 444, height = 356)



        var rpX:Number = lpX + lpW + 6;



        var rpY:Number = lpY;



        var rpW:Number = secW - rpX - 12;



        var rpH:Number = lpH;



        var rpBg:Shape = new Shape();



        rpBg.graphics.beginFill(0xFFFFFF, 0.95);



        rpBg.graphics.lineStyle(1, 0xCBD6E2, 1.0);



        rpBg.graphics.drawRoundRect(rpX, rpY, rpW, rpH, 6, 6);



        rpBg.graphics.endFill();



        this.mDirectorContainer.addChild(rpBg);



        // Right panel header bar



        var rpHeaderBg:Shape = new Shape();



        rpHeaderBg.graphics.beginFill(0xDFE8F2, 1.0);



        rpHeaderBg.graphics.drawRoundRect(rpX, rpY, rpW, 30, 6, 6);



        rpHeaderBg.graphics.endFill();



        this.mDirectorContainer.addChild(rpHeaderBg);



        this.mDirectorCurrentStateTitleTf = makeText("Сценарии: Дома", 12, 0x19456B);



        this.mDirectorCurrentStateTitleTf.x = rpX + 12;



        this.mDirectorCurrentStateTitleTf.y = rpY + 6;



        this.mDirectorContainer.addChild(this.mDirectorCurrentStateTitleTf);



        // Quick action buttons in right header



        var btnResetDef:SimsPillButton = new SimsPillButton("По умолчанию", 98, 22, "director_action", "reset_default", this, false, 10);



        btnResetDef.x = rpX + rpW - 104;



        btnResetDef.y = rpY + 4;



        btnResetDef.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.onDirectorBulkAction("reset_default");



        });



        this.mDirectorContainer.addChild(btnResetDef);



        var btnOffAll:SimsPillButton = new SimsPillButton("Выкл все", 72, 22, "director_action", "disable_all", this, false, 10);



        btnOffAll.x = btnResetDef.x - 78;



        btnOffAll.y = rpY + 4;



        btnOffAll.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.onDirectorBulkAction("disable_all");



        });



        this.mDirectorContainer.addChild(btnOffAll);



        var btnOnAll:SimsPillButton = new SimsPillButton("Вкл все", 68, 22, "director_action", "enable_all", this, false, 10);



        btnOnAll.x = btnOffAll.x - 74;



        btnOnAll.y = rpY + 4;



        btnOnAll.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.onDirectorBulkAction("enable_all");



        });



        this.mDirectorContainer.addChild(btnOnAll);



        // Scrollview for triggers



        this.mDirectorScrollView = new MaxisScrollView(rpW - 4, rpH - 34);



        this.mDirectorScrollView.x = rpX + 2;



        this.mDirectorScrollView.y = rpY + 32;



        this.mDirectorContainer.addChild(this.mDirectorScrollView);



        this.selectDirectorState(this.mDirectorCurrentState || "HOME");



    }



    public function selectDirectorState(stateKey:String):void



    {



        if (!stateKey) return;



        this.mDirectorCurrentState = stateKey;



        this.rebuildDirectorStateButtons();



        var stateTitle:String = "Дома";



        if (stateKey == "VISITING_RELATIVES") stateTitle = "В гостях у родственников";



        else if (stateKey == "VISITING_FRIENDS") stateTitle = "В гостях у друзей";



        else if (stateKey == "COMMUNITY") stateTitle = "Общественные участки";



        if (this.mDirectorCurrentStateTitleTf)



        {



            this.mDirectorCurrentStateTitleTf.text = "Сценарии: " + stateTitle;



        }



        this.rebuildDirectorTriggers();



    }



    public function rebuildDirectorStateButtons():void



    {



        if (!this.mDirectorStateButtonsContainer) return;



        while (this.mDirectorStateButtonsContainer.numChildren > 0)



        {



            this.mDirectorStateButtonsContainer.removeChildAt(0);



        }



        this.mDirectorStateButtons = [];



        var states:Array = this.getDirectorStatesList();



        var btnW:Number = 196;



        var btnH:Number = 42;



        var gap:Number = 6;



        var selfRef:SettingsUI = this;



        for (var i:int = 0; i < states.length; i++)



        {



            var stObj:Object = states[i];



            var stKey:String = String(stObj.id);



            var isSel:Boolean = (stKey == this.mDirectorCurrentState);



            var row:Sprite = new Sprite();



            row.x = 0;



            row.y = i * (btnH + gap);



            row.buttonMode = true;



            row.useHandCursor = true;



            row.mouseChildren = false;



            var bg:Shape = new Shape();



            if (isSel)



            {



                bg.graphics.beginFill(0x2D72B0, 1.0);



                bg.graphics.drawRoundRect(0, 0, btnW, btnH, 6, 6);



                bg.graphics.endFill();



            }



            else



            {



                bg.graphics.beginFill(0xFFFFFF, 0.90);



                bg.graphics.lineStyle(1, 0xCBD6E2, 0.9);



                bg.graphics.drawRoundRect(0, 0, btnW, btnH, 6, 6);



                bg.graphics.endFill();



            }



            row.addChild(bg);



            var titleColor:uint = isSel ? 0xFFFFFF : 0x19456B;



            var descColor:uint = isSel ? 0xD2E6F8 : 0x647B91;



            var tTf:TextField = makeText(String(stObj.title), 12, titleColor);



            tTf.x = 10;



            tTf.y = 4;



            tTf.mouseEnabled = false;



            row.addChild(tTf);



            var dblTf:TextField = makeText(String(stObj.desc), 9, descColor);



            dblTf.x = 10;



            dblTf.y = 22;



            dblTf.mouseEnabled = false;



            row.addChild(dblTf);



            (function(k:String, spr:Sprite, isSelected:Boolean):void {



                spr.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



                    selfRef.selectDirectorState(k);



                });



                if (!isSelected)



                {



                    spr.addEventListener(MouseEvent.ROLL_OVER, function(e:MouseEvent):void {



                        spr.alpha = 0.85;



                    });



                    spr.addEventListener(MouseEvent.ROLL_OUT, function(e:MouseEvent):void {



                        spr.alpha = 1.0;



                    });



                }



            })(stKey, row, isSel);



            this.mDirectorStateButtonsContainer.addChild(row);



            this.mDirectorStateButtons.push(row);



        }



    }



    public function rebuildDirectorTriggers():void



    {



        if (!this.mDirectorScrollView) return;



        var scrollContent:Sprite = this.mDirectorScrollView.getContent();



        while (scrollContent.numChildren > 0)



        {



            scrollContent.removeChildAt(0);



        }



        this.mDirectorCheckboxesByTrigger = {};



        var triggers:Array = this.getDirectorTriggersForState(this.mDirectorCurrentState);



        var secW:Number = this.mDirectorScrollView.getViewportWidth();



        var rowH:Number = 42;



        var selfRef:SettingsUI = this;



        var statePrefix:String = this.mDirectorCurrentState.toLowerCase() + "_";



        for (var i:int = 0; i < triggers.length; i++)



        {



            var item:Object = triggers[i];



            var trigKey:String = String(item.key);



            var fullKey:String = statePrefix + trigKey;



            var row:Sprite = new Sprite();



            row.y = i * rowH;



            row.buttonMode = true;



            row.useHandCursor = true;



            row.mouseChildren = true;



            var rowBg:Shape = new Shape();



            rowBg.graphics.beginFill(0xFFFFFF, 0.001);



            rowBg.graphics.drawRect(0, 0, secW, rowH);



            rowBg.graphics.endFill();



            row.addChild(rowBg);



            var sep:Shape = new Shape();



            sep.graphics.lineStyle(1, 0xCBD6E2, 0.35);



            sep.graphics.moveTo(12, rowH - 1);



            sep.graphics.lineTo(secW - 12, rowH - 1);



            row.addChild(sep);



            var titleTf:TextField = makeBoundedText(String(item.title), 12, 0x19456B, secW - 180);



            titleTf.x = 14;



            titleTf.y = 4;



            row.addChild(titleTf);



            var meta:Object = this.getDirectorTriggerMeta(trigKey);



            var immLabelStr:String = meta.immediate ? "Мгновенное" : "Фоновое";



            var badgeStr:String = "[" + immLabelStr + " | Пр: " + meta.priority + (meta.is_custom ? " *" : "") + "]";



            var badgeCol:uint = meta.is_custom ? 0x0A63A5 : 0x7A8D9F;



            var badgeTf:TextField = makeText(badgeStr, 10, badgeCol);



            badgeTf.x = Math.min(secW - 170, 14 + titleTf.textWidth + 8);



            badgeTf.y = 5;



            row.addChild(badgeTf);



            var descTf:TextField = makeBoundedText(String(item.desc), 10, 0x647B91, secW - 75);



            descTf.x = 14;



            descTf.y = 22;



            row.addChild(descTf);



            var isEnabled:Boolean = (this.mDirectorDisabledTriggers[fullKey] !== true);



            var cb:SimsCheckbox = new SimsCheckbox(trigKey, isEnabled, function(k:String, st:Boolean):void {



                selfRef.onDirectorTriggerToggle(k, st);



            });



            cb.x = secW - 46;



            cb.y = Math.floor((rowH - 20) / 2);



            row.addChild(cb);



            this.mDirectorCheckboxesByTrigger[trigKey] = cb;



            (function(trigItem:Object):void {
                row.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {
                    try
                    {
                        var targetRow:Sprite = e.currentTarget as Sprite;
                        if (targetRow != null && targetRow.mouseX < (secW - 50))
                        {
                            selfRef.showDirectorTriggerModal(trigItem);
                        }
                    }
                    catch (clickErr:Error)
                    {
                        if (ExternalInterface.available)
                        {
                            ExternalInterface.call("CallGameService", "PostServerCommand", {
                                "command": "synapse.ui_log",
                                "commandArgs": ["[FLASH] row.CLICK ERROR: " + clickErr.message]
                            }, false);
                        }
                    }
                });
            })(item);



            row.addEventListener(MouseEvent.ROLL_OVER, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var rBg:Shape = targetRow.getChildAt(0) as Shape;



                    if (rBg != null)



                    {



                        rBg.graphics.clear();



                        rBg.graphics.beginFill(0x2E80C2, 0.08);



                        rBg.graphics.drawRoundRect(6, 1, secW - 12, rowH - 2, 6, 6);



                        rBg.graphics.endFill();



                    }



                }



            });



            row.addEventListener(MouseEvent.ROLL_OUT, function(e:MouseEvent):void {



                var targetRow:Sprite = e.currentTarget as Sprite;



                if (targetRow != null)



                {



                    var rBg:Shape = targetRow.getChildAt(0) as Shape;



                    if (rBg != null)



                    {



                        rBg.graphics.clear();



                        rBg.graphics.beginFill(0xFFFFFF, 0.001);



                        rBg.graphics.drawRect(0, 0, secW, rowH);



                        rBg.graphics.endFill();



                    }



                }



            });



            scrollContent.addChild(row);



        }



        var totalH:Number = triggers.length * rowH;



        this.mDirectorScrollView.updateLayout(totalH);



        this.mDirectorScrollView.resetScroll();



    }



        public function showModalAlert(titleStr:String, msgStr:String):void
    {
        this.closeDirectorModal();
        var selfRef:SettingsUI = this;
        var overlay:Sprite = new Sprite();
        var dimmer:Sprite = new Sprite();
        dimmer.graphics.beginFill(0x0A103D, 0.46);
        dimmer.graphics.drawRect(-500, -500, WIN_W + 1000, WIN_H + 1000);
        dimmer.graphics.endFill();
        overlay.addChild(dimmer);

        dimmer.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {
            e.stopPropagation();
            selfRef.closeDirectorModal();
        });

        var pW:Number = 480;
        var pH:Number = 220;
        var panel:Sprite = this.createModalPanel(pW, pH, titleStr, function():void {
            selfRef.closeDirectorModal();
        });

        var msgTf:TextField = makeText(msgStr, 11, 0x1A344B);
        msgTf.x = 24;
        msgTf.y = 48;
        msgTf.width = pW - 48;
        msgTf.wordWrap = true;
        msgTf.multiline = true;
        panel.addChild(msgTf);

        var btnOk:SimsPillButton = new SimsPillButton("Понятно", 110, 26, "custom_action", "", this, false, 11);
        btnOk.x = Math.round((pW - 110) / 2);
        btnOk.y = pH - 38;
        btnOk.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {
            e.stopPropagation();
            selfRef.closeDirectorModal();
        });
        panel.addChild(btnOk);

        overlay.addChild(panel);
        this.mDirectorModalOverlay = overlay;
        this.mWindow.addChild(overlay);
    }

    public function onDirectorMasterToggle(val:Boolean):void
    {
        if (val && this.mSimplifiedEnabled)
        {
            if (this.mDirectorMasterCheckbox != null)
            {
                this.mDirectorMasterCheckbox.setState(false);
            }
            this.mDirectorEnabled = false;
            this.showModalAlert("Внимание: Конфликт режимов", "Невозможно включить Режиссёр общения!\n\nУпрощённое автономное общение уже активно. Одновременно может работать только один из этих двух режимов.\n\nПожалуйста, сначала отключите Упрощённое общение во вкладке «Упрощённое общение».");
            return;
        }
        this.mDirectorEnabled = val;
        if (ExternalInterface.available)
        {
            ExternalInterface.call("CallGameService", "PostServerCommand", {
                "command": "synapse.set_director_master",
                "commandArgs": [val ? "1" : "0"]
            }, false);
        }
    }

    public function onSimplifiedMasterToggle(val:Boolean):void
    {
        if (val && this.mDirectorEnabled)
        {
            if (this.mSimplifiedMasterCheckbox != null)
            {
                this.mSimplifiedMasterCheckbox.setState(false);
            }
            this.mSimplifiedEnabled = false;
            this.showModalAlert("Внимание: Конфликт режимов", "Невозможно включить Упрощённое общение!\n\nРежиссёр живого общения уже активен. Одновременно может работать только один из этих двух режимов.\n\nПожалуйста, сначала отключите Режиссёра общения во вкладке «Режиссёр общения».");
            return;
        }
        this.mSimplifiedEnabled = val;
        if (ExternalInterface.available)
        {
            ExternalInterface.call("CallGameService", "PostServerCommand", {
                "command": "synapse.set_simplified_master",
                "commandArgs": [val ? "1" : "0"]
            }, false);
        }
    }



    public function onDirectorTriggerToggle(trigKey:String, val:Boolean):void



    {



        var fullKey:String = this.mDirectorCurrentState.toLowerCase() + "_" + trigKey;



        if (val)



        {



            delete this.mDirectorDisabledTriggers[fullKey];



        }



        else



        {



            this.mDirectorDisabledTriggers[fullKey] = true;



        }



        if (ExternalInterface.available)



        {



            ExternalInterface.call("CallGameService", "PostServerCommand", {



                "command": "synapse.set_director_trigger",



                "commandArgs": [this.mDirectorCurrentState, trigKey, val ? "1" : "0"]



            }, false);



        }



    }



    public function onDirectorBulkAction(action:String):void



    {



        var triggers:Array = this.getDirectorTriggersForState(this.mDirectorCurrentState);



        var statePrefix:String = this.mDirectorCurrentState.toLowerCase() + "_";



        for (var i:int = 0; i < triggers.length; i++)



        {



            var item:Object = triggers[i];



            var trigKey:String = String(item.key);



            var fullKey:String = statePrefix + trigKey;



            var targetVal:Boolean = (action != "disable_all");



            if (targetVal)



            {



                delete this.mDirectorDisabledTriggers[fullKey];



            }



            else



            {



                this.mDirectorDisabledTriggers[fullKey] = true;



            }



            if (action == "reset_default")



            {



                delete this.mDirectorOverrides[trigKey];



            }



            var cb:SimsCheckbox = this.mDirectorCheckboxesByTrigger[trigKey] as SimsCheckbox;



            if (cb != null)



            {



                cb.setState(targetVal);



            }



        }



        if (ExternalInterface.available)



        {



            ExternalInterface.call("CallGameService", "PostServerCommand", {



                "command": "synapse.bulk_director_state",



                "commandArgs": [this.mDirectorCurrentState, action]



            }, false);



        }



    }



    public function refreshDirectorUI():void



    {



        if (this.mDirectorMasterCheckbox)



        {



            this.mDirectorMasterCheckbox.setState(this.mDirectorEnabled);



        }



        this.selectDirectorState(this.mDirectorCurrentState || "HOME");



    }



    public function getDirectorStatesList():Array



    {



        return [



            { id: "HOME", title: "Дома", desc: "Свой жилой участок и быт" },



            { id: "VISITING_RELATIVES", title: "В гостях у родственников", desc: "Семейные встречи и родня" },



            { id: "VISITING_FRIENDS", title: "В гостях у друзей", desc: "Вечеринки, игры и посиделки" },



            { id: "COMMUNITY", title: "Общественные участки", desc: "Бары, парки, спортзалы, клубы" }



        ];



    }



    public function openBalloonStudio():void

    {

        try

        {

            Boot.sendServerLog("openBalloonStudio: opening studio HUD");

            var targetSimId:String = (this.mCurrentSimId != null && this.mCurrentSimId != "") ? this.mCurrentSimId : "0";

            var targetSimName:String = (this.mCurrentSimName != null && this.mCurrentSimName != "") ? this.mCurrentSimName : "Сим";



            // 1. Release modality so game camera (WASD, mouse) is completely free

            try

            {

                var cmMod:Object = getDefinitionByName("olympus.io.CommunicationManager");

                cmMod.CallUIService("SetWidgetModality", {

                    "widgetName": "FacebookDisplay",

                    "bOn": false

                });

                cmMod.CallGameService("SetTextFieldInput", false);

            }

            catch (eMod:Error) {}



            // 2. Stop running window animations

            removeEventListener(Event.ENTER_FRAME, this.onAnimFrame);

            this.mAnimMode = 0;



            // 3. Close popups, dropdowns and modals

            this.closeActivePopup();

            this.closeDirectorModal();

            this.dropStageFocus();



            // 4. Hide window and completely wipe out the modal dimmer overlay

            if (this.mWindow != null) this.mWindow.visible = false;

            if (this.mDimmer != null)

            {

                this.mDimmer.graphics.clear();

                this.mDimmer.visible = false;

            }



            // 5. Build and attach the studio HUD panel

            this.showStudioPanel(targetSimId, targetSimName);



            // 6. Request Python to pause game and locate active sim if needed

            if (ExternalInterface.available)

            {

                ExternalInterface.call("CallGameService", "PostServerCommand", {

                    "command": "synapse.balloon_studio_start",

                    "commandArgs": []

                }, false);

            }

        }

        catch (errObs:Error)

        {

            Boot.sendServerLog("openBalloonStudio Error: " + errObs.message);

        }

    }



    public function showStudioPanel(simId:String, simName:String):void

    {

        try

        {

            Boot.sendServerLog("showStudioPanel: creating BalloonStudioUI for " + simId + " (" + simName + ")");

            this.hideStudioPanel();



            try

            {

                var cmMod2:Object = getDefinitionByName("olympus.io.CommunicationManager");

                cmMod2.CallUIService("SetWidgetModality", {

                    "widgetName": "FacebookDisplay",

                    "bOn": false

                });

                cmMod2.CallGameService("SetTextFieldInput", false);

            }

            catch (eMod2:Error) {}



            removeEventListener(Event.ENTER_FRAME, this.onAnimFrame);

            this.mAnimMode = 0;



            if (this.mWindow != null) this.mWindow.visible = false;

            if (this.mDimmer != null)

            {

                this.mDimmer.graphics.clear();

                this.mDimmer.visible = false;

            }



            this.visible = true;

            this.mouseEnabled = false;

            this.mouseChildren = true;



            var bInst:Boot = Boot.sActiveInstance;

            this.mStudioPanel = new BalloonStudioUI(bInst, this, simId, simName);

            this.mStudioPanel.x = 24;

            this.mStudioPanel.y = 50;

            this.addChild(this.mStudioPanel);

            this.setChildIndex(this.mStudioPanel, this.numChildren - 1);



            Boot.showStudioPreviewBalloon(simId, simName, "Привет! Это предпросмотр бабла над симом. Всё настраивается в реальном времени!", "speech");

            Boot.sendServerLog("showStudioPanel: successfully attached to SettingsUI");

        }

        catch (errSsp:Error)

        {

            Boot.sendServerLog("showStudioPanel Error: " + errSsp.message);

        }

    }



    public function onStudioStartFromPython(simId:String, simName:String):void

    {

        this.mCurrentSimId = simId;

        this.mCurrentSimName = simName;

        if (this.mStudioPanel != null)

        {

            Boot.showStudioPreviewBalloon(simId, simName, "Привет! Это предпросмотр бабла над симом. Всё настраивается в реальном времени!", "speech");

        }

        else

        {

            this.showStudioPanel(simId, simName);

        }

    }



    public function hideStudioPanel():void

    {

        if (this.mStudioPanel != null)

        {

            if (this.mStudioPanel.parent != null)

            {

                this.mStudioPanel.parent.removeChild(this.mStudioPanel);

            }

            this.mStudioPanel = null;

        }

    }



    public function closeBalloonStudio(saved:Boolean):void

    {

        this.hideStudioPanel();

        Boot.clearStudioPreviewBalloon();



        try

        {

            var cmFo:Object = getDefinitionByName("olympus.io.CommunicationManager");

            cmFo.CallGameService("SetTextFieldInput", false);

        }

        catch (eFo:Error) {}



        if (ExternalInterface.available)

        {

            ExternalInterface.call("CallGameService", "PostServerCommand", {

                "command": "synapse.balloon_studio_stop",

                "commandArgs": []

            }, false);

        }



        this.drawDimmer();

        if (this.mDimmer != null) this.mDimmer.visible = true;

        if (this.mWindow != null) this.mWindow.visible = true;

        this.setModal(true);

        this.selectTab(6); // Stay on Notifications & Balloons tab

    }



    public function closeDirectorModal():void



    {



        if (this.mDirectorModalOverlay != null)



        {



            try {



                var cmFo:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cmFo.CallGameService("SetTextFieldInput", false);



            } catch(eFo:Error) {}



            if (this.mDirectorModalOverlay.parent != null)



            {



                this.mDirectorModalOverlay.parent.removeChild(this.mDirectorModalOverlay);



            }



            this.mDirectorModalOverlay = null;



            this.grabStageFocus();



        }



    }



        public function createModalMultilineInput(parentSp:Sprite, xPos:Number, yPos:Number, w:Number, h:Number, initVal:String, maxLen:int = 2500):TextField

    {

        var border:Shape = new Shape();

        border.graphics.beginFill(COL_BOX_BORDER, 1.0);

        border.graphics.drawRoundRect(xPos, yPos, w, h, 4, 4);

        border.graphics.endFill();

        parentSp.addChild(border);



        var inner:Shape = new Shape();

        inner.graphics.beginFill(0xFFFFFF, 1.0);

        inner.graphics.drawRoundRect(xPos + 1, yPos + 1, w - 2, h - 2, 3, 3);

        inner.graphics.endFill();

        parentSp.addChild(inner);



        var tf:TextField = new TextField();

        tf.type = "input";

        tf.embedFonts = true;

        tf.selectable = true;

        tf.mouseEnabled = true;

        tf.multiline = true;

        tf.wordWrap = true;

        tf.maxChars = maxLen;

        tf.text = initVal;

        tf.x = xPos + 4;

        tf.y = yPos + 4;

        tf.width = w - 8;

        tf.height = h - 8;



        var fmt:TextFormat = new TextFormat("$TextFont", 11, COL_LABEL_DARK, false);

        tf.defaultTextFormat = fmt;

        tf.setTextFormat(fmt);



        tf.addEventListener(FocusEvent.FOCUS_IN, function(e:FocusEvent):void {

            try {

                var cmFi:Object = getDefinitionByName("olympus.io.CommunicationManager");

                cmFi.CallGameService("SetTextFieldInput", true);

            } catch(eFi:Error) {}

        });



        tf.addEventListener(FocusEvent.FOCUS_OUT, function(e:FocusEvent):void {

            try {

                var cmFo:Object = getDefinitionByName("olympus.io.CommunicationManager");

                cmFo.CallGameService("SetTextFieldInput", false);

            } catch(eFo:Error) {}

        });



        parentSp.addChild(tf);

        return tf;

    }



    public function createModalInput(parentSp:Sprite, xPos:Number, yPos:Number, w:Number, h:Number, initVal:String, maxLen:int = 5, restrictChars:String = "0-9"):TextField



    {



        var border:Shape = new Shape();



        border.graphics.beginFill(COL_BOX_BORDER, 1.0);



        border.graphics.drawRoundRect(xPos, yPos, w, h, 4, 4);



        border.graphics.endFill();



        parentSp.addChild(border);



        var inner:Shape = new Shape();



        inner.graphics.beginFill(0xFFFFFF, 1.0);



        inner.graphics.drawRoundRect(xPos + 1, yPos + 1, w - 2, h - 2, 3, 3);



        inner.graphics.endFill();



        parentSp.addChild(inner);



        var tf:TextField = new TextField();



        tf.type = "input";



        tf.embedFonts = true;



        tf.selectable = true;



        tf.mouseEnabled = true;



        tf.multiline = false;



        tf.wordWrap = false;



        if (restrictChars && restrictChars.length > 0)



        {



            tf.restrict = restrictChars;



        }



        tf.maxChars = maxLen;



        tf.text = initVal;



        tf.x = xPos + 4;



        tf.y = yPos + 2;



        tf.width = w - 8;



        tf.height = h - 4;



        var fmt:TextFormat = new TextFormat("$TextFont", 12, COL_LABEL_DARK, false);



        tf.defaultTextFormat = fmt;



        tf.setTextFormat(fmt);



        tf.addEventListener(FocusEvent.FOCUS_IN, function(e:FocusEvent):void {



            try {



                var cmFi:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cmFi.CallGameService("SetTextFieldInput", true);



            } catch(eFi:Error) {}



        });



        tf.addEventListener(FocusEvent.FOCUS_OUT, function(e:FocusEvent):void {



            try {



                var cmFo:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cmFo.CallGameService("SetTextFieldInput", false);



            } catch(eFo:Error) {}



        });



        parentSp.addChild(tf);



        return tf;



    }



    public function getDirectorTriggerDefaultMeta(key:String):Object
    {
        var immediateKeys:Object = {
            "cooking_burnt": 90,
            "object_broke": 90,
            "dirt_mess": 80,
            "fire_hazard": 96,
            "burglar_theft": 96,
            "grim_reaper_death": 98,
            "cheating_caught": 95,
            "breakup_divorce": 94,
            "sudden_fight": 95,
            "fight_lost": 88,
            "fight_won": 88,
            "prank_backfire": 86,
            "bladder_emergency": 88,
            "intruder_spotted": 92,
            "relative_warm_welcome": 92,
            "guest_arrival_greeting": 92,
            "bartender_order": 85,
            "cafe_coffee": 85,
            "paid_bills": 88
        };

        var routineKeys:Object = {
            "clean_house": 70,
            "cooking_masterpiece": 80,
            "repair_success": 78,
            "morning_wake": 65,
            "night_sleep": 65,
            "relaxing_bath": 60,
            "bill_arrived": 75,
            "low_energy": 65,
            "hunger_starving": 70,
            "garden_harvest": 72,
            "spoiled_food": 74,
            "guest_knock": 85,
            "welcomed_guest": 85,
            "maid_arrival": 82,
            "repairman_arrival": 82,
            "painting_art": 72,
            "instrument_play": 72,
            "gaming_session": 75,
            "tv_movie": 75,
            "book_reading": 68,
            "fitness_training": 73,
            "relative_greetings": 90,
            "family_tea": 78,
            "reminisce_past": 70,
            "advice_critique": 76,
            "family_gossip": 75,
            "gift_exchange": 82,
            "kid_compliments": 75,
            "ask_money_loan": 80,
            "heirloom_talk": 74,
            "friend_chill": 70,
            "console_coop": 75,
            "share_secrets": 78,
            "party_music": 80,
            "drinks_chat": 76,
            "dating_advice": 76,
            "borrow_item": 74,
            "board_games": 76,
            "bar_cheers": 75,
            "gym_workout": 73,
            "park_walk": 68,
            "library_quiet": 70,
            "nightclub_dance": 78
        };

        var noAnimKeys:Object = {
            "fire_hazard": true, "burglar_theft": true, "grim_reaper_death": true,
            "cheating_caught": true, "breakup_divorce": true, "sudden_fight": true, "fight_lost": true, "fight_won": true,
            "prank_backfire": true, "bladder_emergency": true, "intruder_spotted": true, "relaxing_bath": true,
            "night_sleep": true, "board_games": true, "chess_game": true,
            "ww_sex_caught": true, "ww_peeping": true
        };
        var defAnim:Boolean = (noAnimKeys[key] !== true);

        if (immediateKeys[key] != null)
        {
            return { immediate: true, priority: int(immediateKeys[key]), enable_anim: defAnim, anim_type: "AUTO" };
        }
        if (routineKeys[key] != null)
        {
            return { immediate: false, priority: int(routineKeys[key]), enable_anim: defAnim, anim_type: "AUTO" };
        }
        return { immediate: false, priority: 60, enable_anim: defAnim, anim_type: "AUTO" };
    }

    public function getDirectorTriggerMeta(key:String):Object
    {
        var def:Object = this.getDirectorTriggerDefaultMeta(key);
        if (this.mDirectorOverrides && this.mDirectorOverrides[key] != null)
        {
            var ov:Object = this.mDirectorOverrides[key];
            return {
                immediate: Boolean(ov.immediate),
                priority: int(ov.priority),
                custom_prompt: (ov.custom_prompt !== undefined) ? String(ov.custom_prompt) : null,
                enable_anim: (ov.enable_anim !== undefined) ? Boolean(ov.enable_anim) : Boolean(def.enable_anim),
                anim_type: (ov.anim_type !== undefined && String(ov.anim_type) != "") ? String(ov.anim_type) : String(def.anim_type),
                is_custom: true,
                def_immediate: def.immediate,
                def_priority: def.priority,
                def_enable_anim: def.enable_anim,
                def_anim_type: def.anim_type
            };
        }
        return {
            immediate: def.immediate,
            priority: def.priority,
            custom_prompt: null,
            enable_anim: def.enable_anim,
            anim_type: def.anim_type,
            is_custom: false,
            def_immediate: def.immediate,
            def_priority: def.priority,
            def_enable_anim: def.enable_anim,
            def_anim_type: def.anim_type
        };
    }

    private function createModalPanel(pW:Number, pH:Number, titleStr:String, onClose:Function):Sprite



    {



        var panel:Sprite = new Sprite();



        panel.x = Math.round((WIN_W - pW) / 2);



        panel.y = Math.round((WIN_H - pH) / 2);



        // 1. Soft multi-layer drop shadow (Scaleform-safe vector shadows)



        var shadow1:Shape = new Shape();



        shadow1.graphics.beginFill(0x000000, 0.08);



        shadow1.graphics.drawRoundRect(-5, -2, pW + 10, pH + 10, 16, 16);



        shadow1.graphics.endFill();



        panel.addChild(shadow1);



        var shadow2:Shape = new Shape();



        shadow2.graphics.beginFill(0x000000, 0.16);



        shadow2.graphics.drawRoundRect(-2, 0, pW + 4, pH + 5, 14, 14);



        shadow2.graphics.endFill();



        panel.addChild(shadow2);



        // 2. White main dialog body



        var bodyBg:Shape = new Shape();



        bodyBg.graphics.beginFill(0xFFFFFF, 1.0);



        bodyBg.graphics.drawRoundRect(0, 0, pW, pH, 12, 12);



        bodyBg.graphics.endFill();



        panel.addChild(bodyBg);



        // 3. Subtle outer border (matching main window frame)



        var outerBorder:Shape = new Shape();



        outerBorder.graphics.lineStyle(1.5, 0xBAC7D5, 1.0, true);



        outerBorder.graphics.drawRoundRect(0, 0, pW, pH, 12, 12);



        panel.addChild(outerBorder);



        // 4. Header Bar: Maxis Steel-Blue COL_SEC_HEADER (height = 32px)



        var barH:Number = 32;



        var hdrTop:Shape = new Shape();



        hdrTop.graphics.beginFill(COL_SEC_HEADER, 1.0);



        hdrTop.graphics.drawRoundRect(0, 0, pW, barH, 12, 12);



        hdrTop.graphics.endFill();



        panel.addChild(hdrTop);



        var hdrFlatBot:Shape = new Shape();



        hdrFlatBot.graphics.beginFill(COL_SEC_HEADER, 1.0);



        hdrFlatBot.graphics.drawRect(0, barH - 8, pW, 8);



        hdrFlatBot.graphics.endFill();



        panel.addChild(hdrFlatBot);



        var hdrSep:Shape = new Shape();



        hdrSep.graphics.beginFill(0x8A9CAE, 1.0);



        hdrSep.graphics.drawRect(0, barH - 1, pW, 1);



        hdrSep.graphics.endFill();



        panel.addChild(hdrSep);



        // Header Title text (12px bold white)



        var titleTf:TextField = makeText(titleStr, 12, 0xFFFFFF);



        titleTf.x = 16;



        titleTf.y = 7;



        panel.addChild(titleTf);



        // 5. Native Circular [X] Close Button (20x20)



        var closeBtn:Sprite = new Sprite();



        closeBtn.buttonMode = true;



        closeBtn.mouseChildren = false;



        closeBtn.x = pW - 27;



        closeBtn.y = 6;



        var closeBg:Shape = new Shape();



        var closeIcon:Shape = new Shape();



        closeBtn.addChild(closeBg);



        closeBtn.addChild(closeIcon);



        closeBg.graphics.beginFill(0x000000, 0.12);



        closeBg.graphics.drawCircle(10, 11, 10);



        closeBg.graphics.endFill();



        closeBg.graphics.beginFill(0x7F8D9D, 1.0);



        closeBg.graphics.drawCircle(10, 10, 10);



        closeBg.graphics.endFill();



        var cMat:Matrix = new Matrix();



        cMat.createGradientBox(18, 18, Math.PI / 2, 1, 1);



        closeBg.graphics.beginGradientFill(



            GradientType.LINEAR,



            [0xFFFFFF, 0xDFE6EE],



            [1.0, 1.0],



            [0, 255],



            cMat



        );



        closeBg.graphics.drawCircle(10, 10, 8.8);



        closeBg.graphics.endFill();



        closeIcon.graphics.lineStyle(2.0, 0x19456B, 1.0);



        closeIcon.graphics.moveTo(6.8, 6.8);



        closeIcon.graphics.lineTo(13.2, 13.2);



        closeIcon.graphics.moveTo(13.2, 6.8);



        closeIcon.graphics.lineTo(6.8, 13.2);



        closeBtn.addEventListener(MouseEvent.ROLL_OVER, function(e:MouseEvent):void {



            closeIcon.graphics.clear();



            closeIcon.graphics.lineStyle(2.0, COL_HOVER_GREEN, 1.0);



            closeIcon.graphics.moveTo(6.8, 6.8);



            closeIcon.graphics.lineTo(13.2, 13.2);



            closeIcon.graphics.moveTo(13.2, 6.8);



            closeIcon.graphics.lineTo(6.8, 13.2);



        });



        closeBtn.addEventListener(MouseEvent.ROLL_OUT, function(e:MouseEvent):void {



            closeIcon.graphics.clear();



            closeIcon.graphics.lineStyle(2.0, 0x19456B, 1.0);



            closeIcon.graphics.moveTo(6.8, 6.8);



            closeIcon.graphics.lineTo(13.2, 13.2);



            closeIcon.graphics.moveTo(13.2, 6.8);



            closeIcon.graphics.lineTo(6.8, 13.2);



        });



        closeBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            if (onClose != null) onClose();



        });



        panel.addChild(closeBtn);



        // 6. Maxis Footer Bar (height = 46px at bottom)



        var footerH:Number = 46;



        var footerY:Number = pH - footerH;



        var footBg:Shape = new Shape();



        var footMat:Matrix = new Matrix();



        footMat.createGradientBox(pW, footerH, Math.PI / 2, 0, footerY);



        footBg.graphics.beginGradientFill(



            GradientType.LINEAR,



            [COL_FOOTER_TOP, COL_FOOTER_BOT],



            [1.0, 1.0],



            [0, 255],



            footMat



        );



        footBg.graphics.drawRoundRect(0, footerY, pW, footerH, 12, 12);



        footBg.graphics.endFill();



        panel.addChild(footBg);



        var footTopFlat:Shape = new Shape();



        footTopFlat.graphics.beginFill(COL_FOOTER_TOP, 1.0);



        footTopFlat.graphics.drawRect(0, footerY, pW, 10);



        footTopFlat.graphics.endFill();



        panel.addChild(footTopFlat);



        var footSep:Shape = new Shape();



        footSep.graphics.beginFill(0x9FA9BD, 1.0);



        footSep.graphics.drawRect(0, footerY, pW, 1);



        footSep.graphics.endFill();



        panel.addChild(footSep);



        panel.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            e.stopPropagation();



        });



        return panel;



    }



    public function showDirectorTimersModal():void



    {



        this.closeDirectorModal();



        var overlay:Sprite = new Sprite();



        var dimmer:Sprite = new Sprite();



        dimmer.graphics.beginFill(0x0A103D, 0.46);



        dimmer.graphics.drawRect(-500, -500, WIN_W + 1000, WIN_H + 1000);



        dimmer.graphics.endFill();



        overlay.addChild(dimmer);



        var selfRef:SettingsUI = this;



        dimmer.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.closeDirectorModal();



        });



        var pW:Number = 500;



        var pH:Number = 265;



        var panel:Sprite = this.createModalPanel(pW, pH, "Настройка таймеров Режиссёра", function():void {



            selfRef.closeDirectorModal();



        });



        var lbl1:TextField = makeText("Пауза тишины в семье (сек):", 11, 0x19456B);



        lbl1.x = 24;



        lbl1.y = 48;



        panel.addChild(lbl1);



        var inSilence:TextField = this.createModalInput(panel, 260, 44, 75, 24, String(this.mDirectorSilenceSec || 240), 5, "0-9");



        var hint1:TextField = makeText("(по умолч: 240с / 4 мин)", 10, 0x647B91);



        hint1.x = 344;



        hint1.y = 48;



        panel.addChild(hint1);



        var lbl2:TextField = makeText("Пауза между теми же симами (сек):", 11, 0x19456B);



        lbl2.x = 24;



        lbl2.y = 86;



        panel.addChild(lbl2);



        var inPair:TextField = this.createModalInput(panel, 260, 82, 75, 24, String(this.mDirectorPairSec || 450), 5, "0-9");



        var hint2:TextField = makeText("(по умолч: 450с / 7.5 мин)", 10, 0x647B91);



        hint2.x = 344;



        hint2.y = 86;



        panel.addChild(hint2);



        var lbl3:TextField = makeText("Задержка при входе на лот (сек):", 11, 0x19456B);



        lbl3.x = 24;



        lbl3.y = 124;



        panel.addChild(lbl3);



        var inGrace:TextField = this.createModalInput(panel, 260, 120, 75, 24, String(this.mDirectorGraceSec || 60), 5, "0-9");



        var hint3:TextField = makeText("(по умолч: 60с / 1 мин)", 10, 0x647B91);



        hint3.x = 344;



        hint3.y = 124;



        panel.addChild(hint3);



        var infoTf:TextField = makeText("Указывает время реальной игры (без учета игровой паузы).", 10, 0x4E6E8E);



        infoTf.x = 24;



        infoTf.y = 162;



        panel.addChild(infoTf);



        var btnSave:SimsPillButton = new SimsPillButton("Сохранить", 110, 26, "custom_action", "", this, false, 11);



        btnSave.x = 24;



        btnSave.y = pH - 36;



        btnSave.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            var sVal:int = parseInt(inSilence.text) || 240;



            var pVal:int = parseInt(inPair.text) || 450;



            var gVal:int = parseInt(inGrace.text) || 60;



            selfRef.mDirectorSilenceSec = sVal;



            selfRef.mDirectorPairSec = pVal;



            selfRef.mDirectorGraceSec = gVal;



            if (ExternalInterface.available)



            {



                ExternalInterface.call("CallGameService", "PostServerCommand", {



                    "command": "synapse.set_director_timers",



                    "commandArgs": [String(sVal), String(pVal), String(gVal)]



                }, false);



            }



            selfRef.closeDirectorModal();



        });



        panel.addChild(btnSave);



        var btnDef:SimsPillButton = new SimsPillButton("По умолчанию", 124, 26, "custom_action", "", this, false, 11);



        btnDef.x = 146;



        btnDef.y = pH - 36;



        btnDef.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            inSilence.text = "240";



            inPair.text = "450";



            inGrace.text = "60";



        });



        panel.addChild(btnDef);



        var btnCancel:SimsPillButton = new SimsPillButton("Отмена", 90, 26, "custom_action", "", this, false, 11);



        btnCancel.x = pW - 114;



        btnCancel.y = pH - 36;



        btnCancel.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.closeDirectorModal();



        });



        panel.addChild(btnCancel);



        overlay.addChild(panel);



        this.mDirectorModalOverlay = overlay;



        this.mWindow.addChild(overlay);



    }



    public function showDirectorTriggerModal(item:Object):void
    {
        try
        {
            if (item == null) return;
            this.closeDirectorModal();

            var trigKey:String = String(item.key);
            var meta:Object = this.getDirectorTriggerMeta(trigKey);
            var selfRef:SettingsUI = this;

            var overlay:Sprite = new Sprite();
            var dimmer:Sprite = new Sprite();
            dimmer.graphics.beginFill(0x0A103D, 0.46);
            dimmer.graphics.drawRect(-500, -500, WIN_W + 1000, WIN_H + 1000);
            dimmer.graphics.endFill();
            overlay.addChild(dimmer);

            dimmer.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {
                e.stopPropagation();
                selfRef.closeDirectorModal();
            });

            var pW:Number = 530;

            var pH:Number = 405;

            var panel:Sprite = this.createModalPanel(pW, pH, "Настройка сценария: " + String(item.title), function():void {
                selfRef.closeDirectorModal();
            });

            var promptHeaderTf:TextField = makeText("Повод и инструкция сценария (Промт):", 11, 0x19456B);
            promptHeaderTf.x = 24;
            promptHeaderTf.y = 38;
            panel.addChild(promptHeaderTf);

            var curPrompt:String = (meta.custom_prompt != null && meta.custom_prompt != "") ? String(meta.custom_prompt) : String(item.desc);
            var inPrompt:TextField = this.createModalMultilineInput(panel, 24, 58, pW - 48, 64, curPrompt, 1500);

            var modeHeaderTf:TextField = makeText("Режим выполнения действия (выберите один):", 11, 0x19456B);
            modeHeaderTf.x = 24;
            modeHeaderTf.y = 130;
            panel.addChild(modeHeaderTf);

            var isImm:Boolean = Boolean(meta.immediate);
            var cbImm:SimsCheckbox;
            var cbBg:SimsCheckbox;

            cbImm = new SimsCheckbox("trig_imm", isImm, function(k:String, st:Boolean):void {
                if (st) {
                    cbBg.setState(false);
                } else {
                    cbBg.setState(true);
                }
            });
            cbImm.x = 24;
            cbImm.y = 152;
            panel.addChild(cbImm);

            var immLabel:TextField = makeText("Мгновенное действие (срабатывает сразу, игнорирует таймер тишины)", 11, 0x1A344B);
            immLabel.x = 52;
            immLabel.y = 152;
            panel.addChild(immLabel);

            cbBg = new SimsCheckbox("trig_bg", !isImm, function(k:String, st:Boolean):void {
                if (st) {
                    cbImm.setState(false);
                } else {
                    cbImm.setState(true);
                }
            });
            cbBg.x = 24;
            cbBg.y = 178;
            panel.addChild(cbBg);

            var bgLabel:TextField = makeText("Фоновое действие (соблюдает стандартную паузу тишины в семье)", 11, 0x1A344B);
            bgLabel.x = 52;
            bgLabel.y = 178;
            panel.addChild(bgLabel);

            var prioHeaderTf:TextField = makeText("Приоритет сценария:", 11, 0x19456B);
            prioHeaderTf.x = 24;
            prioHeaderTf.y = 208;
            panel.addChild(prioHeaderTf);

            var prioDefTf:TextField = makeText("(Заводской: " + (meta.def_priority != null ? meta.def_priority : 50) + ")", 11, 0x647B91);
            prioDefTf.x = 154;
            prioDefTf.y = 208;
            panel.addChild(prioDefTf);

            var inPrio:TextField = this.createModalInput(panel, 24, 230, 60, 24, String(meta.priority != null ? meta.priority : 50), 3, "0-9");

            var prioHintTf:TextField = makeText("Число от 1 до 999. Чем выше приоритет, тем раньше этот повод запустится.", 10, 0x4E6E8E);
            prioHintTf.x = 94;
            prioHintTf.y = 234;
            panel.addChild(prioHintTf);

            // Section: Conversation action (sim_Chat)
            var animHeaderTf:TextField = makeText("Общение персонажей:", 11, 0x19456B);
            animHeaderTf.x = 24;
            animHeaderTf.y = 266;
            panel.addChild(animHeaderTf);

            var curAnimEnabled:Boolean = (meta.enable_anim !== undefined) ? Boolean(meta.enable_anim) : true;
            var curAnimType:String = "AUTO";

            var cbAnim:SimsCheckbox = new SimsCheckbox("trig_anim", curAnimEnabled, function(k:String, st:Boolean):void {
                curAnimEnabled = st;
            });
            cbAnim.x = 24;
            cbAnim.y = 288;
            panel.addChild(cbAnim);

            var animLabel:TextField = makeText("Начинать разговор (Поболтать)", 11, 0x1A344B);
            animLabel.x = 52;
            animLabel.y = 288;
            panel.addChild(animLabel);

            var animHintTf:TextField = makeText("Если выключено, персонажи не отвлекаются от текущих дел, а реплики идут только облачками мыслей.", 10, 0x4E6E8E);

            animHintTf.x = 24;

            animHintTf.y = 316;

            animHintTf.width = pW - 48;

            animHintTf.wordWrap = true;

            animHintTf.multiline = true;

            panel.addChild(animHintTf);

            var btnSave:SimsPillButton = new SimsPillButton("Сохранить", 110, 26, "custom_action", "", this, false, 11);
            btnSave.x = 24;
            btnSave.y = pH - 36;
            btnSave.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {
                e.stopPropagation();
                var finalImm:Boolean = cbImm.getState();
                var finalPrio:int = parseInt(inPrio.text) || meta.def_priority || 50;
                var finalPrompt:String = inPrompt.text;
                selfRef.mDirectorOverrides[trigKey] = {
                    immediate: finalImm,
                    priority: finalPrio,
                    custom_prompt: finalPrompt,
                    enable_anim: curAnimEnabled,
                    anim_type: curAnimType
                };
                if (ExternalInterface.available)
                {
                    ExternalInterface.call("CallGameService", "PostServerCommand", {
                        "command": "synapse.set_director_trigger_meta",
                        "commandArgs": [trigKey, finalImm ? "1" : "0", String(finalPrio), selfRef.encodeSafeStr(finalPrompt), curAnimEnabled ? "1" : "0", curAnimType]
                    }, false);
                }
                selfRef.closeDirectorModal();
                selfRef.rebuildDirectorTriggers();
            });
            panel.addChild(btnSave);

            var btnDef:SimsPillButton = new SimsPillButton("По умолчанию", 124, 26, "custom_action", "", this, false, 11);
            btnDef.x = 146;
            btnDef.y = pH - 36;
            btnDef.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {
                e.stopPropagation();
                delete selfRef.mDirectorOverrides[trigKey];
                inPrompt.text = String(item.desc);
                if (ExternalInterface.available)
                {
                    ExternalInterface.call("CallGameService", "PostServerCommand", {
                        "command": "synapse.reset_director_trigger_meta",
                        "commandArgs": [trigKey]
                    }, false);
                }
                selfRef.closeDirectorModal();
                selfRef.rebuildDirectorTriggers();
            });
            panel.addChild(btnDef);

            var btnCancel:SimsPillButton = new SimsPillButton("Отмена", 90, 26, "custom_action", "", this, false, 11);
            btnCancel.x = pW - 114;
            btnCancel.y = pH - 36;
            btnCancel.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {
                e.stopPropagation();
                selfRef.closeDirectorModal();
            });
            panel.addChild(btnCancel);

            overlay.addChild(panel);
            this.mDirectorModalOverlay = overlay;
            this.mWindow.addChild(overlay);

            if (ExternalInterface.available)
            {
                ExternalInterface.call("CallGameService", "PostServerCommand", {
                    "command": "synapse.ui_log",
                    "commandArgs": ["[FLASH] showDirectorTriggerModal SUCCESS for: " + trigKey]
                }, false);
            }
        }
        catch (err:Error)
        {
            if (ExternalInterface.available)
            {
                ExternalInterface.call("CallGameService", "PostServerCommand", {
                    "command": "synapse.ui_log",
                    "commandArgs": ["[FLASH] showDirectorTriggerModal ERROR: " + err.message + " | " + err.getStackTrace()]
                }, false);
            }
        }
    }

    private function getDirectorEmergencyTriggers():Array



    {



        return [



            { key: "fire_hazard", title: "Пожар на участке", desc: "Огонь, паника, попытка потушить пламя" },



            { key: "burglar_theft", title: "Кража или пропажа", desc: "Пропажа ценных вещей, тревога" },



            { key: "grim_reaper_death", title: "Визит Смерти", desc: "Гибель персонажа, траур, мольбы о пощаде" },



            { key: "cheating_caught", title: "Измена с поличным", desc: "Ревность, крики, предательство" },



            { key: "breakup_divorce", title: "Разрыв или развод", desc: "Тяжёлый разговор о расставании" },



            { key: "sudden_fight", title: "Внезапная драка", desc: "Ярость, кулаки, семейный скандал" },



            { key: "fight_lost", title: "Поражение в потасовке", desc: "Позор и ушибы после драки" },



            { key: "fight_won", title: "Победа в потасовке", desc: "Торжество и адреналин после победы" },



            { key: "prank_backfire", title: "Неудачная шалость", desc: "Пранк пошёл не по плану" },



            { key: "bladder_emergency", title: "Конфуз с нуждой", desc: "Критическая ситуация с туалетом" },



            { key: "hygiene_emergency", title: "Ужасная вонь", desc: "Невыносимый запах и грязь" },



            { key: "embarrassed_mood", title: "Сильный стыд", desc: "Желание провалиться сквозь землю" }



        ];



    }



    private function getDirectorHobbyTriggers():Array



    {



        return [



            { key: "painting_art", title: "Создание картины", desc: "Вдохновение у холста, мазки кистью" },



            { key: "instrument_play", title: "Игра на инструменте", desc: "Музыкальные пассажи, тренировка слуха" },



            { key: "gaming_session", title: "Видеоигры", desc: "Азарт турнира, прохождение игры" },



            { key: "tv_movie", title: "Просмотр кино", desc: "Обсуждение сериала или фильма" },



            { key: "book_reading", title: "Чтение книги", desc: "Погружение в захватывающий роман" },



            { key: "fitness_training", title: "Фитнес и тренировка", desc: "Упражнения, пот, прокачка пресса" }



        ];



    }



    public function getDirectorTriggersForState(stateKey:String):Array



    {



        var res:Array = [];



        var emerg:Array = this.getDirectorEmergencyTriggers();



        var hobbies:Array = this.getDirectorHobbyTriggers();



        if (stateKey == "HOME")



        {



            var homeRoutine:Array = [



                { key: "cooking_burnt", title: "Пригорание еды", desc: "Запах гари, испорченный завтрак/ужин" },



                { key: "cooking_masterpiece", title: "Кулинарный шедевр", desc: "Восхищение вкусом и подачей" },



                { key: "object_broke", title: "Поломка предмета", desc: "Сломанная сантехника, искрящая техника" },



                { key: "repair_success", title: "Успешный ремонт", desc: "Гордость за починку своими руками" },



                { key: "dirt_mess", title: "Грязь и беспорядок", desc: "Неубранная посуда, пыль и мусор" },



                { key: "clean_house", title: "Чистота и порядок", desc: "Приятная домашняя атмосфера" },



                { key: "morning_wake", title: "Утреннее пробуждение", desc: "Сонливость, планы на день, кофе" },



                { key: "night_sleep", title: "Отход ко сну", desc: "Усталость, пожелание спокойной ночи" },



                { key: "relaxing_bath", title: "Пенная ванна", desc: "Отдых и расслабление после дня" },



                { key: "bill_arrived", title: "Счёт за дом", desc: "Высокие счета за коммунальные услуги" },



                { key: "paid_bills", title: "Оплата счетов", desc: "Облегчение после оплаты квитанций" },



                { key: "low_energy", title: "Сильное переутомление", desc: "Глаза слипаются, нет сил" },



                { key: "hunger_starving", title: "Зверский голод", desc: "Живот урчит, срочно нужна еда" },



                { key: "garden_harvest", title: "Сбор урожая", desc: "Созревшие овощи, фрукты и цветы" },



                { key: "spoiled_food", title: "Испортившаяся еда", desc: "Залежавшаяся еда в холодильнике" },



                { key: "guest_knock", title: "Стук в дверь / гости", desc: "Неожиданные или званые гости на пороге" },



                { key: "welcomed_guest", title: "Радушный приём", desc: "Приглашение в дом, кофе и чай" },



                { key: "maid_arrival", title: "Визит горничной", desc: "Уборка дома прислугой" },



                { key: "repairman_arrival", title: "Визит мастера", desc: "Приезд мастера по ремонту" },



                { key: "nanny_arrival", title: "Приход няни", desc: "Присмотр за детьми и малышами" },



                { key: "gardener_arrival", title: "Визит садовника", desc: "Уход за растениями на участке" },



                { key: "delivery_food", title: "Доставка еды", desc: "Курьер с горячей пиццей или заказом" },



                { key: "ring_doorbell", title: "Звонок в дверь", desc: "Кто-то стоит у входа" },



                { key: "intruder_spotted", title: "Непрошеный гость", desc: "Подозрительный незнакомец у дверей" },



                { key: "borrow_sugar", title: "Соседская просьба", desc: "Сосед зашёл одолжить продукты" },



                { key: "saying_goodbye", title: "Проводы гостей", desc: "Тёплые объятия на пороге" }



            ];



            res = homeRoutine.concat(emerg).concat(hobbies);



        }



        else if (stateKey == "VISITING_RELATIVES")



        {



            var relRoutine:Array = [



                { key: "relative_greetings", title: "Семейные объятия", desc: "Тёплая встреча родных, радость встречи" },



                { key: "family_tea", title: "Семейное чаепитие", desc: "Пироги, душевные беседы за столом" },



                { key: "reminisce_past", title: "Воспоминания о детстве", desc: "Ностальгия, старые семейные фото" },



                { key: "advice_critique", title: "Поучения и критика", desc: "Нравоучения старших родственников" },



                { key: "family_gossip", title: "Родственные сплетни", desc: "Новости о жизни других членов семьи" },



                { key: "gift_exchange", title: "Обмен подарками", desc: "Приятные презенты и сувениры" },



                { key: "kid_compliments", title: "Похвала детям", desc: "Восхищение успехами младших" },



                { key: "ask_money_loan", title: "Просьба в долг", desc: "Неловкая просьба о финансовой помощи" },



                { key: "heirloom_talk", title: "Разговор о наследстве", desc: "Семейные реликвии и ценности" }



            ];



            res = relRoutine.concat(emerg).concat(hobbies);



        }



        else if (stateKey == "VISITING_FRIENDS")



        {



            var friendRoutine:Array = [



                { key: "friend_chill", title: "Дружеские посиделки", desc: "Уютный отдых, болтовня ни о чём" },



                { key: "console_coop", title: "Совместные видеоигры", desc: "Командные игры, спортивный азарт" },



                { key: "share_secrets", title: "Секреты и сплетни", desc: "Разговоры по душам, тайны" },



                { key: "party_music", title: "Вечеринка и музыка", desc: "Танцы, громкие треки, напитки" },



                { key: "drinks_chat", title: "Коктейли и закуски", desc: "Тосты, смех и дружеские истории" },



                { key: "dating_advice", title: "Советы по свиданиям", desc: "Разбор романтических неудач" },



                { key: "borrow_item", title: "Одолжить вещь", desc: "Просьба дать поиграть или поносить" },



                { key: "board_games", title: "Настольные игры", desc: "Карты, стратегии, забавный спор" }



            ];



            res = friendRoutine.concat(emerg).concat(hobbies);



        }



        else if (stateKey == "COMMUNITY")



        {



            var commRoutine:Array = [



                { key: "bartender_order", title: "Заказ у бармена", desc: "Выпивка у стойки бара, чаевые" },



                { key: "bar_cheers", title: "Тосты и атмосфера бара", desc: "Шумная компания, звон бокалов" },



                { key: "gym_workout", title: "Тренировка в спортзале", desc: "Штанги, тренажёры, мотивация" },



                { key: "park_walk", title: "Прогулка по парку", desc: "Свежий воздух, лавочки, птицы" },



                { key: "library_quiet", title: "Тишина в библиотеке", desc: "Шёпот, шелест страниц, книги" },



                { key: "nightclub_dance", title: "Танцы в клубе", desc: "Танцпол, световое шоу, диджей" },



                { key: "cafe_coffee", title: "Кофе и круассаны", desc: "Столик у окна, заказ бариста" }



            ];



            res = commRoutine.concat(emerg).concat(hobbies);



        }



        return res;



    }





    // =====================================================================
    // УПРОЩЁННОЕ АВТОНОМНОЕ ОБЩЕНИЕ (SIMPLIFIED AUTONOMOUS DIALOGUE)
    // =====================================================================
    public function buildSimplifiedSection():void
    {
        this.mSimplifiedContainer = new Sprite();
        this.mSimplifiedContainer.visible = false;
        this.mWorkspace.addChild(this.mSimplifiedContainer);

        var secW:Number = WORKSPACE_W;
        var barH:Number = 28;
        var secY:Number = 0;
        var secBodyH:Number = 430;
        var selfRef:SettingsUI = this;

        this.drawSectionContainerOn(this.mSimplifiedContainer, secY, secW, barH, secBodyH);

        var secTitle:TextField = makeCenteredText("Упрощённое автономное общение", 13, 0xFFFFFF, secW);
        secTitle.x = 0;
        secTitle.y = secY + 4;
        this.mSimplifiedContainer.addChild(secTitle);

        // TOP BANNER: Master switch
        var topBannerH:Number = 42;
        var topBannerY:Number = secY + barH + 8;

        var bannerBg:Shape = new Shape();
        var bMat:Matrix = new Matrix();
        bMat.createGradientBox(secW - 24, topBannerH, Math.PI / 2, 0, 0);
        bannerBg.graphics.beginGradientFill(
            GradientType.LINEAR,
            [0xECF3FA, 0xDFEAF4],
            [1.0, 1.0],
            [0, 255],
            bMat
        );
        bannerBg.graphics.lineStyle(1, 0xB8CBDC, 0.8, true);
        bannerBg.graphics.drawRoundRect(12, topBannerY, secW - 24, topBannerH, 6, 6);
        this.mSimplifiedContainer.addChild(bannerBg);

        this.mSimplifiedMasterCheckbox = new SimsCheckbox("simplified_master", this.mSimplifiedEnabled, function(k:String, st:Boolean):void {
            selfRef.onSimplifiedMasterToggle(st);
        });
        this.mSimplifiedMasterCheckbox.x = 22;
        this.mSimplifiedMasterCheckbox.y = topBannerY + 11;
        this.mSimplifiedContainer.addChild(this.mSimplifiedMasterCheckbox);

        var masterTitleTf:TextField = makeText("Включить упрощённое автономное общение", 12, 0x19456B);
        masterTitleTf.x = 48;
        masterTitleTf.y = topBannerY + 5;
        this.mSimplifiedContainer.addChild(masterTitleTf);

        var masterHintTf:TextField = makeText("Диалоги генерируются прямо во время стандартного общения симов без сбивания действий", 10, 0x647B91);
        masterHintTf.x = 48;
        masterHintTf.y = topBannerY + 22;
        this.mSimplifiedContainer.addChild(masterHintTf);

        // CARD 1: Description / Explanation
        var card1Y:Number = topBannerY + topBannerH + 10;
        var card1H:Number = 88;

        var descBg:Shape = new Shape();
        descBg.graphics.beginFill(0xF7FAFD, 0.9);
        descBg.graphics.lineStyle(1, 0xD4E2EE, 0.8, true);
        descBg.graphics.drawRoundRect(12, card1Y, secW - 24, card1H, 6, 6);
        descBg.graphics.endFill();
        this.mSimplifiedContainer.addChild(descBg);

        var descTitle:TextField = makeText("Как работает этот режим:", 11, 0x19456B);
        descTitle.x = 24;
        descTitle.y = card1Y + 8;
        this.mSimplifiedContainer.addChild(descTitle);

        var descTf:TextField = makeText(
            "Облегчённый альтернативный режим. Когда симы из активной семьи спонтанно общаются друг с другом (стандартное действие «Поболтать»), мод с заданной вероятностью генерирует естественный контекстный диалог из 2 реплик и отображает 3D облачка над головами персонажей.\n\nДействия симов не сбиваются, а очередь команд не засоряется сторонними взаимодействиями.",
            10,
            0x4E6E8E
        );
        descTf.x = 24;
        descTf.y = card1Y + 28;
        descTf.width = secW - 48;
        descTf.wordWrap = true;
        descTf.multiline = true;
        this.mSimplifiedContainer.addChild(descTf);

        // CARD 2: Settings Controls (Silence Timer & Probability)
        var card2Y:Number = card1Y + card1H + 10;
        var card2H:Number = 205;

        var settBg:Shape = new Shape();
        settBg.graphics.beginFill(0xFFFFFF, 0.8);
        settBg.graphics.lineStyle(1, 0xD4E2EE, 0.8, true);
        settBg.graphics.drawRoundRect(12, card2Y, secW - 24, card2H, 6, 6);
        settBg.graphics.endFill();
        this.mSimplifiedContainer.addChild(settBg);

        var settTitle:TextField = makeText("Настройки частоты и отображения:", 11, 0x19456B);
        settTitle.x = 24;
        settTitle.y = card2Y + 10;
        this.mSimplifiedContainer.addChild(settTitle);

        // Row 1: Silence cooldown
        var row1Y:Number = card2Y + 36;
        var lblSilence:TextField = makeText("Пауза тишины между диалогами (мин):", 11, 0x1A344B);
        lblSilence.x = 24;
        lblSilence.y = row1Y + 3;
        this.mSimplifiedContainer.addChild(lblSilence);

        var curMinSilence:int = Math.max(1, Math.round(this.mSimplifiedSilenceSec / 60));
        this.mSimplifiedInSilence = this.createModalInput(this.mSimplifiedContainer, 290, row1Y, 55, 24, String(curMinSilence), 3, "0-9");

        var hintSilence:TextField = makeText("(по умолч: 3 мин / 180 сек)", 10, 0x647B91);
        hintSilence.x = 355;
        hintSilence.y = row1Y + 4;
        this.mSimplifiedContainer.addChild(hintSilence);

        // Row 2: Trigger chance %
        var row2Y:Number = row1Y + 36;
        var lblChance:TextField = makeText("Шанс генерации диалога при общении (%):", 11, 0x1A344B);
        lblChance.x = 24;
        lblChance.y = row2Y + 3;
        this.mSimplifiedContainer.addChild(lblChance);

        this.mSimplifiedInChance = this.createModalInput(this.mSimplifiedContainer, 290, row2Y, 55, 24, String(this.mSimplifiedChancePct || 40), 3, "0-9");

        var hintChance:TextField = makeText("(от 10% до 100%, по умолч: 40%)", 10, 0x647B91);
        hintChance.x = 355;
        hintChance.y = row2Y + 4;
        this.mSimplifiedContainer.addChild(hintChance);

        // Row 3: Balloon display checkbox
        var row3Y:Number = row2Y + 36;
        this.mSimplifiedCbBalloon = new SimsCheckbox("simp_bal", this.mSimplifiedBalloon, function(k:String, st:Boolean):void {
            selfRef.mSimplifiedBalloon = st;
        });
        this.mSimplifiedCbBalloon.x = 24;
        this.mSimplifiedCbBalloon.y = row3Y;
        this.mSimplifiedContainer.addChild(this.mSimplifiedCbBalloon);

        var lblBal:TextField = makeText("Показывать 3D облачка речи над персонажами", 11, 0x1A344B);
        lblBal.x = 52;
        lblBal.y = row3Y;
        this.mSimplifiedContainer.addChild(lblBal);

        // Row 4: Notification display checkbox
        var row4Y:Number = row3Y + 28;
        this.mSimplifiedCbNotif = new SimsCheckbox("simp_notif", this.mSimplifiedNotif, function(k:String, st:Boolean):void {
            selfRef.mSimplifiedNotif = st;
        });
        this.mSimplifiedCbNotif.x = 24;
        this.mSimplifiedCbNotif.y = row4Y;
        this.mSimplifiedContainer.addChild(this.mSimplifiedCbNotif);

        var lblNotif:TextField = makeText("Показывать текстовые уведомления в правом углу экрана", 11, 0x1A344B);
        lblNotif.x = 52;
        lblNotif.y = row4Y;
        this.mSimplifiedContainer.addChild(lblNotif);

        // Row 5: Save button
        var btnSaveSimp:SimsPillButton = new SimsPillButton("Сохранить настройки", 160, 26, "custom_action", "", this, false, 11);
        btnSaveSimp.x = 24;
        btnSaveSimp.y = card2Y + card2H - 34;
        btnSaveSimp.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {
            e.stopPropagation();
            var minVal:int = parseInt(selfRef.mSimplifiedInSilence.text) || 3;
            var chVal:int = parseInt(selfRef.mSimplifiedInChance.text) || 40;
            if (minVal < 1) minVal = 1;
            if (minVal > 60) minVal = 60;
            if (chVal < 5) chVal = 5;
            if (chVal > 100) chVal = 100;

            selfRef.mSimplifiedSilenceSec = minVal * 60;
            selfRef.mSimplifiedChancePct = chVal;
            selfRef.mSimplifiedBalloon = selfRef.mSimplifiedCbBalloon.getState();
            selfRef.mSimplifiedNotif = selfRef.mSimplifiedCbNotif.getState();

            if (ExternalInterface.available)
            {
                ExternalInterface.call("CallGameService", "PostServerCommand", {
                    "command": "synapse.set_simplified_timers",
                    "commandArgs": [String(selfRef.mSimplifiedSilenceSec), String(selfRef.mSimplifiedChancePct)]
                }, false);
                ExternalInterface.call("CallGameService", "PostServerCommand", {
                    "command": "synapse.set_simplified_display",
                    "commandArgs": [selfRef.mSimplifiedBalloon ? "1" : "0", selfRef.mSimplifiedNotif ? "1" : "0"]
                }, false);
            }
        });
        this.mSimplifiedContainer.addChild(btnSaveSimp);
    }

    public function refreshSimplifiedUI():void
    {
        if (this.mSimplifiedMasterCheckbox != null)
        {
            this.mSimplifiedMasterCheckbox.setState(this.mSimplifiedEnabled);
        }
        if (this.mSimplifiedInSilence != null)
        {
            var curMin:int = Math.max(1, Math.round(this.mSimplifiedSilenceSec / 60));
            this.mSimplifiedInSilence.text = String(curMin);
        }
        if (this.mSimplifiedInChance != null)
        {
            this.mSimplifiedInChance.text = String(this.mSimplifiedChancePct || 40);
        }
        if (this.mSimplifiedCbBalloon != null)
        {
            this.mSimplifiedCbBalloon.setState(this.mSimplifiedBalloon);
        }
        if (this.mSimplifiedCbNotif != null)
        {
            this.mSimplifiedCbNotif.setState(this.mSimplifiedNotif);
        }
    }

    public function buildExperimentalSection():void



    {



        this.mExperimentalContainer = new Sprite();



        this.mExperimentalContainer.visible = false;



        this.mWorkspace.addChild(this.mExperimentalContainer);



        var secW:Number = WORKSPACE_W;



        var barH:Number = 28;



        var secY:Number = 0;



        var secBodyH:Number = 430;



        var selfRef:SettingsUI = this;



        this.drawSectionContainerOn(this.mExperimentalContainer, secY, secW, barH, secBodyH);



        var secTitle:TextField = makeCenteredText("Экспериментальные функции и механики", 13, 0xFFFFFF, secW);



        secTitle.x = 0;



        secTitle.y = secY + 4;



        this.mExperimentalContainer.addChild(secTitle);



        var hintBg:Shape = new Shape();



        var hMat:Matrix = new Matrix();



        hMat.createGradientBox(secW - 24, 26, Math.PI / 2, 0, 0);



        hintBg.graphics.beginGradientFill(



            GradientType.LINEAR,



            [0xECF3FA, 0xDFEAF4],



            [1.0, 1.0],



            [0, 255],



            hMat



        );



        hintBg.graphics.lineStyle(1, 0xB8CBDC, 0.8, true);



        hintBg.graphics.drawRoundRect(12, secY + barH + 6, secW - 24, 26, 6, 6);



        hintBg.graphics.endFill();



        this.mExperimentalContainer.addChild(hintBg);



        var hintTf:TextField = makeText("Экспериментальные улучшения контекста, логики ИИ и геймплея The Sims 4.", 11, 0x1E466B);



        hintTf.x = 22;



        hintTf.y = secY + barH + 11;



        this.mExperimentalContainer.addChild(hintTf);



        var scrollW:Number = secW - 24;



        var scrollH:Number = secBodyH - 42;



        this.mExperimentalScrollView = new MaxisScrollView(scrollW, scrollH);



        this.mExperimentalScrollView.x = 12;



        this.mExperimentalScrollView.y = secY + barH + 36;



        this.mExperimentalContainer.addChild(this.mExperimentalScrollView);



        var bottomCap:Shape = new Shape();



        bottomCap.graphics.beginFill(0xFFFFFF, 1.0);



        bottomCap.graphics.drawRoundRect(1, secY + barH + secBodyH - 8, secW - 2, 7, 4, 4);



        bottomCap.graphics.endFill();



        this.mExperimentalContainer.addChild(bottomCap);



    }



    public function reflowExperimentalAccordions():void



    {



        var currY:Number = 0;



        var gap:Number = 6;



        for (var i:int = 0; i < this.mExperimentalAccordionSections.length; i++)



        {



            var sec:MaxisAccordionSection = this.mExperimentalAccordionSections[i] as MaxisAccordionSection;



            if (sec != null)



            {



                sec.y = currY;



                currY += sec.getTotalHeight() + gap;



            }



        }



        if (this.mExperimentalScrollView != null)



        {



            this.mExperimentalScrollView.updateLayout(currY);



        }



    }



    public function getExperimentalGroups():Array



    {



        return [



            {



                "title": "1. ЭКСПЕРИМЕНТАЛЬНЫЙ КОНТЕКСТ И ИИ",



                "items": [



                    {



                        "key": "dynamic_interaction_ui_fallback",



                        "title": "Динамический перехват действий (UI Fallback)",



                        "desc": "Дотягивает текущие действия сима напрямую из интерфейса игры, если стандартный перехватчик не сработал."



                    },



                    {



                        "key": "home_business_context",



                        "title": "Домашний бизнес («Любимое дело»)",



                        "desc": "Учитывает домашний бизнес из «Любимое дело» (роль сима на участке, посетители, режим работы)."



                    },



                    {



                        "key": "trapped_sim_detection",



                        "title": "Определение запертого сима (Дверь / Без выхода)",



                        "desc": "В контексте после имени сима указывает [ЗАПЕРТ] или [ЗАМУРОВАН]."



                    },



                    {



                        "key": "last_thought_context",



                        "title": "Последняя мысль в контексте (За 1 час)",



                        "desc": "В контексте пишется последняя мысль сима за последний час (60 мин)."



                    }



                ]



            },



            {



                "title": "2. ЭКСПЕРИМЕНТАЛЬНЫЙ ГЕЙМПЛЕЙ И МЕХАНИКИ",



                "items": [



                    {



                        "key": "direct_dialogue_pause",



                        "title": "Пауза игры во время живого диалога",



                        "desc": "Замораживает игровое время на время генерации ответа собеседника, чтобы симы не разбегались."



                    },



                    {
                        "key": "direct_dialogue_approach_first",
                        "title": "Подойти к собеседнику перед разговором",
                        "desc": "Персонаж сначала подходит к собеседнику на расстояние общения, и только затем открывается окно ввода текста реплики."
                    },
                    {



                        "key": "direct_dialogue_multisim_join",



                        "title": "Подключение к живому общению (Группа и свидетели)",



                        "desc": "Позволяет участникам группового секса и свидетелям рядом подключаться к живому диалогу (через разделитель ///)."



                    },



                    {



                        "key": "alien_male_pregnancy",



                        "title": "Распознавание мужской беременности пришельцами",



                        "desc": "Автоматически связывает беременность персонажей-мужчин с похищением инопланетянами (НЛО)."



                    },



                    {



                        "key": "classic_insane_trait",



                        "title": "Черта «Безумный»",



                        "desc": "Возвращает непредсказуемое поведение черты из The Sims 3 в мысли и реплики персонажа."



                    },



                    {



                        "key": "overheard_conversations",



                        "title": "Память разговоров рядом (Слух и экран)",



                        "desc": "Симы запоминают чужие разговоры и переписки, находясь поблизости."



                    },



                    {



                        "key": "third_party_dossier",



                        "title": "Справка о сторонних персонажах (Досье)",



                        "desc": "Справка в контекст при упоминании чужих имен, типажей, соседей или родни."



                    }



                ]



            }



        ];



    }



    public function rebuildExperimentalItems():void



    {



        if (!this.mExperimentalScrollView) return;



        var prevScroll:Number = this.mExperimentalScrollView.getScrollY();



        var scrollContent:Sprite = this.mExperimentalScrollView.getContent();



        while (scrollContent.numChildren > 0)



        {



            scrollContent.removeChildAt(0);



        }



        this.mExperimentalAccordionSections = [];



        this.mExperimentalCheckboxesByKey = {};



        var groups:Array = this.getExperimentalGroups();



        var secW:Number = this.mExperimentalScrollView.getViewportWidth();



        var selfRef:SettingsUI = this;



        for (var gIdx:int = 0; gIdx < groups.length; gIdx++)



        {



            var grp:Object = groups[gIdx];



            var secTitle:String = String(grp.title);



            var secKey:String = "exp_" + secTitle;



            var isInitiallyExpanded:Boolean = (this.mExperimentalExpandedSections[secKey] !== undefined) ?



                Boolean(this.mExperimentalExpandedSections[secKey]) : true;



            var accSec:MaxisAccordionSection = new MaxisAccordionSection(



                secTitle,



                secW,



                28,



                isInitiallyExpanded,



                function(tSec:MaxisAccordionSection):void {



                    var k:String = "exp_" + tSec.title;



                    selfRef.mExperimentalExpandedSections[k] = tSec.isExpanded;



                    selfRef.reflowExperimentalAccordions();



                }



            );



            var grpItems:Array = grp.items as Array;



            if (grpItems != null && grpItems.length > 0)



            {



                this.populateExperimentalSectionItems(accSec.content, grpItems, secW, 0);



            }



            scrollContent.addChild(accSec);



            this.mExperimentalAccordionSections.push(accSec);



        }



        this.mExperimentalScrollView.setOwnerSections(this.mExperimentalAccordionSections);



        this.reflowExperimentalAccordions();



        if (prevScroll > 0)



        {



            this.mExperimentalScrollView.scrollTo(prevScroll);



        }



        else



        {



            this.mExperimentalScrollView.resetScroll();



        }



    }



    private function populateExperimentalSectionItems(container:Sprite, items:Array, secW:Number, startY:Number = 0):void

    {

        var selfRef:SettingsUI = this;

        var curY:Number = startY;



        for (var i:int = 0; i < items.length; i++)

        {

            var item:Object = items[i];

            var isMultisimRow:Boolean = (item.key == "direct_dialogue_multisim_join");

            var rowH:Number = isMultisimRow ? 78 : 40;



            var row:Sprite = new Sprite();

            row.y = curY;

            curY += rowH;



            row.buttonMode = true;

            row.useHandCursor = true;

            row.mouseChildren = true;



            var rowBg:Shape = new Shape();

            rowBg.graphics.beginFill(0xFFFFFF, 0.001);

            rowBg.graphics.drawRect(0, 0, secW, rowH);

            rowBg.graphics.endFill();

            row.addChild(rowBg);



            var sep:Shape = new Shape();

            sep.graphics.lineStyle(1, 0xCBD6E2, 0.40);

            sep.graphics.moveTo(16, rowH - 1);

            sep.graphics.lineTo(secW - 16, rowH - 1);

            row.addChild(sep);



            var titleTf:TextField = makeBoundedText(String(item.title), 12, 0x19456B, secW - 75);

            titleTf.x = 20;

            titleTf.y = 4;

            row.addChild(titleTf);



            var descTf:TextField;

            if (isMultisimRow)

            {

                descTf = new TextField();

                descTf.embedFonts = true;

                descTf.selectable = false;

                descTf.mouseEnabled = false;

                descTf.multiline = true;

                descTf.wordWrap = true;

                descTf.autoSize = TextFieldAutoSize.LEFT;

                var descFmt:TextFormat = new TextFormat("$TextFont", 10, 0x647B91, false);

                descTf.defaultTextFormat = descFmt;

                descTf.text = String(item.desc);

                descTf.width = secW - 75;

                descTf.x = 20;

                descTf.y = 20;

                row.addChild(descTf);



                var btnRules:SimsPillButton = new SimsPillButton("Настройка промтов", 140, 22, "custom_action", "", this, false, 10);

                btnRules.x = 20;

                btnRules.y = 48;

                btnRules.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {

                    e.stopPropagation();

                    selfRef.openMultisimRulesModal();

                });

                row.addChild(btnRules);

            }

            else

            {

                descTf = makeBoundedText(String(item.desc), 10, 0x647B91, secW - 75);

                descTf.x = 20;

                descTf.y = 20;

                row.addChild(descTf);

            }



            var isFlagOn:Boolean = (this.mExperimentalFlagsState[item.key] !== undefined) ?

                Boolean(this.mExperimentalFlagsState[item.key]) : false;



            var cb:SimsCheckbox = new SimsCheckbox(String(item.key), isFlagOn, function(k:String, st:Boolean):void {

                selfRef.onExperimentalToggleClick(k, st);

            });



            cb.x = secW - 46;

            cb.y = isMultisimRow ? 10 : Math.floor((rowH - 20) / 2);

            row.addChild(cb);



            this.mExperimentalCheckboxesByKey[item.key] = cb;



            row.addEventListener(MouseEvent.ROLL_OVER, function(e:MouseEvent):void {

                var targetRow:Sprite = e.currentTarget as Sprite;

                if (targetRow != null)

                {

                    var rBg:Shape = targetRow.getChildAt(0) as Shape;

                    if (rBg != null)

                    {

                        rBg.graphics.clear();

                        rBg.graphics.beginFill(0x2E80C2, 0.08);

                        rBg.graphics.drawRoundRect(8, 1, secW - 16, rowH - 2, 6, 6);

                        rBg.graphics.endFill();

                    }

                }

            });



            row.addEventListener(MouseEvent.ROLL_OUT, function(e:MouseEvent):void {

                var targetRow:Sprite = e.currentTarget as Sprite;

                if (targetRow != null)

                {

                    var rBg:Shape = targetRow.getChildAt(0) as Shape;

                    if (rBg != null)

                    {

                        rBg.graphics.clear();

                        rBg.graphics.beginFill(0xFFFFFF, 0.001);

                        rBg.graphics.drawRect(0, 0, secW, rowH);

                        rBg.graphics.endFill();

                    }

                }

            });



            row.name = String(item.key);



            row.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {

                var targetRow:Sprite = e.currentTarget as Sprite;

                if (targetRow != null)

                {

                    var flagKey:String = targetRow.name;

                    var rowCb:SimsCheckbox = selfRef.mExperimentalCheckboxesByKey[flagKey] as SimsCheckbox;

                    if (rowCb != null)

                    {

                        var curSt:Boolean = rowCb.getState();

                        rowCb.setState(!curSt);

                        selfRef.onExperimentalToggleClick(flagKey, !curSt);

                    }

                }

            });



            container.addChild(row);

        }

    }



    public function openMultisimRulesModal():void

    {

        this.closeDirectorModal();

        var selfRef:SettingsUI = this;

        var overlay:Sprite = new Sprite();

        var dimmer:Sprite = new Sprite();

        dimmer.graphics.beginFill(0x0A103D, 0.46);

        dimmer.graphics.drawRect(-500, -500, WIN_W + 1000, WIN_H + 1000);

        dimmer.graphics.endFill();

        overlay.addChild(dimmer);

        dimmer.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {

            selfRef.closeDirectorModal();

        });



        // Request latest rules from python

        if (ExternalInterface.available)

        {

            ExternalInterface.call("CallGameService", "PostServerCommand", {

                "command": "synapse.get_multisim_rules",

                "commandArgs": []

            }, false);

        }



        var pW:Number = 580;

        var pH:Number = 460;

        var panel:Sprite = this.createModalPanel(pW, pH, "Промты подключения к общению", function():void {

            selfRef.closeDirectorModal();

        });



        var subTf:TextField = makeText("Настройте правила подключения участников и свидетелей через «///»:", 11, 0x19456B);

        subTf.x = 24;

        subTf.y = 42;

        panel.addChild(subTf);



        var ruleKeys:Array = ["group_chat", "bystander", "sex_group", "sex_bystander"];

        var ruleTitles:Array = [

            "1. Групповой диалог (3+ симов)",

            "2. Свидетели рядом (Диалог)",

            "3. Групповой интим (Участники)",

            "4. Свидетели интима (В комнате)"

        ];

        var ruleHints:Array = [

            "Правило для участников круга общения (3+ симов, отвечают по очереди через ///):",

            "Правило для свидетелей разговора рядом (молчат и встревают только при обращении):",

            "Правило для участников совместного группового секса / секса втроём (стоны, реплики через ///):",

            "Правило для свидетелей/наблюдателей интимного акта в комнате (молчание, [DO=join_sex]):"

        ];



        var tabBtns:Array = [];

        var activeIdx:int = 0;

        if (this.mActiveMultisimRuleKey == "bystander") activeIdx = 1;

        else if (this.mActiveMultisimRuleKey == "sex_group") activeIdx = 2;

        else if (this.mActiveMultisimRuleKey == "sex_bystander") activeIdx = 3;

        else activeIdx = 0;



        var lblHint:TextField = makeText(ruleHints[activeIdx], 10, 0x5C768D);

        lblHint.x = 24;

        lblHint.y = 126;

        panel.addChild(lblHint);



        var curKey:String = ruleKeys[activeIdx];

        var curVal:String = (this.mMultisimRules[curKey] !== undefined && this.mMultisimRules[curKey] != "") ?

            String(this.mMultisimRules[curKey]) : String(this.mDefaultMultisimRules[curKey]);



        var inArea:TextField = this.createModalMultilineInput(panel, 24, 148, pW - 48, 256, curVal, 2500);

        this.mMultisimRuleInput = inArea;



        var switchTab:Function = function(newIdx:int):void {

            var prevKey:String = ruleKeys[activeIdx];

            selfRef.mMultisimRules[prevKey] = inArea.text;



            activeIdx = newIdx;

            var newKey:String = ruleKeys[activeIdx];

            selfRef.mActiveMultisimRuleKey = newKey;



            lblHint.text = ruleHints[activeIdx];

            var nextVal:String = (selfRef.mMultisimRules[newKey] !== undefined && selfRef.mMultisimRules[newKey] != "") ?

                String(selfRef.mMultisimRules[newKey]) : String(selfRef.mDefaultMultisimRules[newKey]);

            inArea.text = nextVal;



            for (var b:int = 0; b < tabBtns.length; b++)

            {

                var tBtn:SimsPillButton = tabBtns[b] as SimsPillButton;

                if (tBtn != null)

                {

                    tBtn.setSelected(b == activeIdx);

                }

            }

        };



        for (var t:int = 0; t < 4; t++)

        {

            var btnX:Number = (t % 2 == 0) ? 24 : 298;

            var btnY:Number = (t < 2) ? 66 : 94;

            var tabBtn:SimsPillButton = new SimsPillButton(ruleTitles[t], 258, 24, "custom_action", "", this, false, 10);

            tabBtn.setSelected(t == activeIdx);

            tabBtn.x = btnX;

            tabBtn.y = btnY;

            (function(idxVal:int):void {

                tabBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {

                    e.stopPropagation();

                    switchTab(idxVal);

                });

            })(t);

            panel.addChild(tabBtn);

            tabBtns.push(tabBtn);

        }



        var btnSave:SimsPillButton = new SimsPillButton("Сохранить", 110, 26, "custom_action", "", this, false, 11);

        btnSave.x = 24;

        btnSave.y = pH - 36;

        btnSave.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {

            var activeKey:String = ruleKeys[activeIdx];

            selfRef.mMultisimRules[activeKey] = inArea.text;



            if (ExternalInterface.available)

            {

                for (var r:int = 0; r < ruleKeys.length; r++)

                {

                    var rk:String = ruleKeys[r];

                    if (selfRef.mMultisimRules[rk] !== undefined)

                    {

                        var ruleText:String = String(selfRef.mMultisimRules[rk]);

                        ExternalInterface.call("CallGameService", "PostServerCommand", {

                            "command": "synapse.set_multisim_rule",

                            "commandArgs": [rk, selfRef.encodeSafeStr(ruleText)]

                        }, false);

                    }

                }

            }

            selfRef.closeDirectorModal();

        });

        panel.addChild(btnSave);



        var btnDef:SimsPillButton = new SimsPillButton("По умолчанию", 124, 26, "custom_action", "", this, false, 11);

        btnDef.x = 146;

        btnDef.y = pH - 36;

        btnDef.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {

            var activeKey:String = ruleKeys[activeIdx];

            var defVal:String = String(selfRef.mDefaultMultisimRules[activeKey]);

            selfRef.mMultisimRules[activeKey] = defVal;

            inArea.text = defVal;



            if (ExternalInterface.available)

            {

                ExternalInterface.call("CallGameService", "PostServerCommand", {

                    "command": "synapse.reset_multisim_rules",

                    "commandArgs": [activeKey]

                }, false);

            }

        });

        panel.addChild(btnDef);



        var btnCancel:SimsPillButton = new SimsPillButton("Закрыть", 90, 26, "custom_action", "", this, false, 11);

        btnCancel.x = pW - 114;

        btnCancel.y = pH - 36;

        btnCancel.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {

            selfRef.closeDirectorModal();

        });

        panel.addChild(btnCancel);



        overlay.addChild(panel);

        this.mDirectorModalOverlay = overlay;

        this.mWindow.addChild(overlay);

    }



    public function onExperimentalToggleClick(flagKey:String, newState:Boolean):void



    {



        this.mExperimentalFlagsState[flagKey] = newState;



        ExternalInterface.call("CallGameService", "PostServerCommand", {



            "command": "synapse.set_experimental_flag",



            "commandArgs": [flagKey, newState ? "1" : "0"]



        });



        if (flagKey == "direct_dialogue_multisim_join")



        {



            this.showDirectDialoguePromptWarningModal(newState);



        }



    }



    public function showDirectDialoguePromptWarningModal(isTurnedOn:Boolean):void



    {



        this.closeDirectorModal();



        var selfRef:SettingsUI = this;



        var overlay:Sprite = new Sprite();



        var dimmer:Sprite = new Sprite();



        dimmer.graphics.beginFill(0x0A103D, 0.46);



        dimmer.graphics.drawRect(-500, -500, WIN_W + 1000, WIN_H + 1000);



        dimmer.graphics.endFill();



        overlay.addChild(dimmer);



        dimmer.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.closeDirectorModal();



        });



        var pW:Number = 560;



        var pH:Number = 330;



        var mTitle:String = isTurnedOn ? "Подключение к общению: ВКЛЮЧЕНО" : "Подключение к общению: ВЫКЛЮЧЕНО";



        var panel:Sprite = this.createModalPanel(pW, pH, mTitle, function():void {



            selfRef.closeDirectorModal();



        });



        var tStatus:String = isTurnedOn ?



            "Функция подключения участников и свидетелей к диалогам активирована." :



            "Функция подключения участников и свидетелей к диалогам отключена. Персонажи будут общаться исключительно тет-а-тет 1-на-1.";



        var tWarning:String = isTurnedOn ?



            "ВНИМАНИЕ: Чтобы персонажи могли подхватывать диалоги через разделитель ///, обновите системные промты в приложении Synapse:\n\n" +



            "  1. Системный промт живого общения (PROMPT_DIRECT_DIALOGUE)\n" +



            "  2. Системный промт интимного диалога (PROMPT_SEX_DIALOGUE)\n\n" +



            "(В Synapse Launcher нажмите кнопку «Сбросить» у этих промтов, либо добавьте инструкции формата /// в кастомные промты)." :



            "ВНИМАНИЕ: Чтобы убрать правила разделителя /// и вернуть одиночные ответы, обновите системные промты в приложении Synapse:\n\n" +



            "  1. Системный промт живого общения (PROMPT_DIRECT_DIALOGUE)\n" +



            "  2. Системный промт интимного диалога (PROMPT_SEX_DIALOGUE)\n\n" +



            "(В Synapse Launcher нажмите кнопку «Сбросить» у этих промтов для возврата к классическим промтам 1-на-1).";



        var statusTf:TextField = new TextField();



        statusTf.embedFonts = true;



        statusTf.selectable = false;



        statusTf.mouseEnabled = false;



        statusTf.multiline = true;



        statusTf.wordWrap = true;



        statusTf.width = pW - 52;



        statusTf.autoSize = TextFieldAutoSize.LEFT;



        var sFmt:TextFormat = new TextFormat("$TextFont", 11, isTurnedOn ? 0x1E7E34 : 0x9E1B1B, true);



        sFmt.leading = 4;



        statusTf.defaultTextFormat = sFmt;



        statusTf.text = tStatus;



        statusTf.x = 26;



        statusTf.y = 44;



        panel.addChild(statusTf);



        var warnTf:TextField = new TextField();



        warnTf.embedFonts = true;



        warnTf.selectable = false;



        warnTf.mouseEnabled = false;



        warnTf.multiline = true;



        warnTf.wordWrap = true;



        warnTf.width = pW - 52;



        warnTf.autoSize = TextFieldAutoSize.LEFT;



        var wFmt:TextFormat = new TextFormat("$TextFont", 11, 0x1A344B, false);



        wFmt.leading = 4;



        warnTf.defaultTextFormat = wFmt;



        warnTf.text = tWarning;



        warnTf.x = 26;



        warnTf.y = statusTf.y + statusTf.height + 14;



        panel.addChild(warnTf);



        var btnOk:SimsPillButton = new SimsPillButton("Понятно", 120, 28, "custom_action", "", this, false, 11);



        btnOk.x = Math.floor((pW - 120) / 2);



        btnOk.y = pH - 42;



        btnOk.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.closeDirectorModal();



        });



        panel.addChild(btnOk);



        overlay.addChild(panel);



        this.mDirectorModalOverlay = overlay;



        this.mWindow.addChild(overlay);



    }



}



// =========================================================================



// ВКЛАДКА ЛЕВОГО МЕНЮ (БЕЗ РАМОК, РОВНОЕ НАТИВНОЕ ЦЕНТРИРОВАНИЕ)



// =========================================================================



class SidebarTab extends Sprite



{



    private var mIndex:int;



    private var mW:Number;



    private var mH:Number;



    private var mOwner:SettingsUI;



    private var mBg:Shape = new Shape();



    private var mTitle:TextField;



    private var mActive:Boolean = false;



    private var mHover:Boolean = false;



    public function SidebarTab(index:int, title:String, w:Number, h:Number, owner:SettingsUI)



    {



        super();



        this.mIndex = index;



        this.mW = w;



        this.mH = h;



        this.mOwner = owner;



        this.buttonMode = true;



        this.mouseChildren = false;



        addChild(this.mBg);



        this.mTitle = SettingsUI.makeCenteredText(title, 14, SettingsUI.COL_ROYAL_BLUE, this.mW);



        this.mTitle.x = 0;



        this.mTitle.y = 9;



        addChild(this.mTitle);



        addEventListener(MouseEvent.ROLL_OVER, this.onRollOver);



        addEventListener(MouseEvent.ROLL_OUT, this.onRollOut);



        addEventListener(MouseEvent.CLICK, this.onClick);



        this.redraw();



    }



    private function onRollOver(e:MouseEvent):void



    {



        this.mHover = true;



        this.redraw();



    }



    private function onRollOut(e:MouseEvent):void



    {



        this.mHover = false;



        this.redraw();



    }



    private function onClick(e:MouseEvent):void



    {



        if (this.mOwner != null)



        {



            this.mOwner.selectTab(this.mIndex);



        }



    }



    public function setActive(val:Boolean):void



    {



        this.mActive = val;



        this.redraw();



    }



    private function redraw():void



    {



        this.mBg.graphics.clear();



        var mat:Matrix = new Matrix();



        mat.createGradientBox(this.mW, this.mH, Math.PI / 2, 0, 0);



        if (this.mActive)



        {



            // Основной сочный градиент активной вкладки (#8FE455 -> #3BBE15)



            this.mBg.graphics.beginGradientFill(



                GradientType.LINEAR,



                [SettingsUI.COL_GREEN_TOP, SettingsUI.COL_GREEN_BOT],



                [1.0, 1.0],



                [0, 255],



                mat



            );



            this.mBg.graphics.drawRect(0, 0, this.mW, this.mH);



            this.mBg.graphics.endFill();



            // Верхний 1px блик и нижний 1px 3D-скос активной вкладки



            this.mBg.graphics.beginFill(0xA6EE72, 1.0);



            this.mBg.graphics.drawRect(0, 0, this.mW, 1);



            this.mBg.graphics.endFill();



            this.mBg.graphics.beginFill(0x2F9E0F, 1.0);



            this.mBg.graphics.drawRect(0, this.mH - 1, this.mW, 1);



            this.mBg.graphics.endFill();



            // Тонкая правая граница вкладки



            this.mBg.graphics.beginFill(0x36AD13, 1.0);



            this.mBg.graphics.drawRect(this.mW - 1, 0, 1, this.mH);



            this.mBg.graphics.endFill();



            this.mTitle.textColor = 0xFFFFFF;



        }



        else



        {



            var topCol:uint = this.mHover ? 0xFFFFFF : SettingsUI.COL_TAB_TOP;



            var botCol:uint = this.mHover ? 0xF2F6FA : SettingsUI.COL_TAB_BOT;



            this.mBg.graphics.beginGradientFill(



                GradientType.LINEAR,



                [topCol, botCol],



                [1.0, 1.0],



                [0, 255],



                mat



            );



            this.mBg.graphics.drawRect(0, 0, this.mW, this.mH);



            this.mBg.graphics.endFill();



            // Верхний 1px чисто-белый блик (#FFFFFF)



            this.mBg.graphics.beginFill(0xFFFFFF, 1.0);



            this.mBg.graphics.drawRect(0, 0, this.mW, 1);



            this.mBg.graphics.endFill();



            // Нижний 1px 3D-бортик (#DFDFDF) и правая кромка (#E2E6EC)



            this.mBg.graphics.beginFill(0xDFDFDF, 1.0);



            this.mBg.graphics.drawRect(0, this.mH - 1, this.mW, 1);



            this.mBg.graphics.endFill();



            this.mBg.graphics.beginFill(0xE2E6EC, 1.0);



            this.mBg.graphics.drawRect(this.mW - 1, 0, 1, this.mH);



            this.mBg.graphics.endFill();



            this.mTitle.textColor = SettingsUI.COL_ROYAL_BLUE;



        }



    }



}



// =========================================================================



// СВОРАЧИВАЮЩАЯСЯ СЕКЦИЯ (АККОРДЕОН) В 100% СТИЛЕ THE SIMS 4



// Развёрнуто: сочный зелёный градиент Maxis с белым текстом и стрелкой ▲



// Свёрнуто: серебристо-серая капсула Maxis с синим текстом и стрелкой ▼



// =========================================================================



class MaxisAccordionSection extends Sprite



{



    private var mTitle:String;



    private var mW:Number;



    private var mBarH:Number;



    private var mExpanded:Boolean;



    private var mHover:Boolean = false;



    private var mHeader:Sprite = new Sprite();



    private var mBg:Shape = new Shape();



    private var mTf:TextField;



    private var mArrow:Shape = new Shape();



    private var mContent:Sprite = new Sprite();



    private var mOnToggleCallback:Function;



    public function get title():String



    {



        return this.mTitle;



    }



    public function MaxisAccordionSection(title:String, w:Number, barH:Number = 28, initiallyExpanded:Boolean = true, onToggle:Function = null)



    {



        super();



        this.mTitle = title;



        this.mW = w;



        this.mBarH = barH;



        this.mExpanded = initiallyExpanded;



        this.mOnToggleCallback = onToggle;



        // 1. Шапка (Header)



        this.mHeader.buttonMode = true;



        this.mHeader.useHandCursor = true;



        this.mHeader.mouseChildren = false;



        this.mHeader.addChild(this.mBg);



        this.mTf = SettingsUI.makeCenteredText(this.mTitle, 12, 0xFFFFFF, this.mW);



        this.mTf.y = Math.max(2, Math.floor((this.mBarH - 20) / 2));



        this.mHeader.addChild(this.mTf);



        this.mHeader.addChild(this.mArrow);



        this.addChild(this.mHeader);



        // 2. Контейнер содержимого (Content)



        this.mContent.y = this.mBarH + 6;



        if (this.mExpanded)



        {



            this.addChild(this.mContent);



            this.mContent.visible = true;



        }



        else



        {



            this.mContent.visible = false;



        }



        this.redraw();



        this.mHeader.addEventListener(MouseEvent.ROLL_OVER, this.onOver);



        this.mHeader.addEventListener(MouseEvent.ROLL_OUT, this.onOut);



        this.mHeader.addEventListener(MouseEvent.CLICK, this.onHeaderClick);



    }



    public function get content():Sprite



    {



        return this.mContent;



    }



    public function get isExpanded():Boolean



    {



        return this.mExpanded;



    }



    public function setExpanded(val:Boolean):void



    {



        if (this.mExpanded != val)



        {



            this.mExpanded = val;



            if (this.mExpanded)



            {



                if (!this.contains(this.mContent))



                {



                    this.addChild(this.mContent);



                }



                this.mContent.visible = true;



            }



            else



            {



                if (this.contains(this.mContent))



                {



                    this.removeChild(this.mContent);



                }



                this.mContent.visible = false;



            }



            this.redraw();



            if (this.mOnToggleCallback != null)



            {



                this.mOnToggleCallback(this);



            }



        }



    }



    public function clipToViewport(scrollY:Number, viewH:Number):void



    {



        // Клиппирование шапки (скрываем, если полностью за пределами вьюпорта)



        var hdrScreenY:Number = this.y - scrollY;



        this.mHeader.visible = (hdrScreenY + this.mBarH > 0 && hdrScreenY < viewH);



        // Клиппирование строк внутри аккордеона



        if (this.mExpanded)



        {



            for (var rIdx:int = 0; rIdx < this.mContent.numChildren; rIdx++)



            {



                var r:DisplayObject = this.mContent.getChildAt(rIdx);



                if (r != null)



                {



                    var rScreenY:Number = this.y + this.mContent.y + r.y - scrollY;



                    r.visible = (rScreenY + 40 > 0 && rScreenY < viewH);



                }



            }



        }



    }



    private function onOver(e:MouseEvent):void



    {



        this.mHover = true;



        this.redraw();



    }



    private function onOut(e:MouseEvent):void



    {



        this.mHover = false;



        this.redraw();



    }



    private function onHeaderClick(e:MouseEvent):void



    {



        this.setExpanded(!this.mExpanded);



    }



    public function getTotalHeight():Number



    {



        if (!this.mExpanded)



        {



            return this.mBarH;



        }



        var ch:Number = (this.mContent.numChildren > 0) ? this.mContent.height : 0;



        return this.mBarH + 6 + ch + 6;



    }



    public function redraw():void



    {



        this.mBg.graphics.clear();



        this.mArrow.graphics.clear();



        var bMat:Matrix = new Matrix();



        bMat.createGradientBox(this.mW, this.mBarH, Math.PI / 2, 0, 0);



        if (this.mExpanded)



        {



            // === РАЗВЁРНУТО: Сочный зелёный градиент The Sims 4 ===



            this.mBg.graphics.beginFill(0x000000, 0.08);



            this.mBg.graphics.drawRoundRect(0, 2, this.mW, this.mBarH, 6, 6);



            this.mBg.graphics.endFill();



            this.mBg.graphics.beginGradientFill(



                GradientType.LINEAR,



                [0x68C430, 0x429D1E, 0x24780E],



                [1.0, 1.0, 1.0],



                [0, 160, 255],



                bMat



            );



            this.mBg.graphics.drawRoundRect(0, 0, this.mW, this.mBarH, 6, 6);



            this.mBg.graphics.endFill();



            this.mBg.graphics.beginFill(0xFFFFFF, this.mHover ? 0.45 : 0.28);



            this.mBg.graphics.drawRoundRect(1, 1, this.mW - 2, 9, 5, 5);



            this.mBg.graphics.endFill();



            this.mTf.textColor = 0xFFFFFF;



            // Стрелочка ВВЕРХ (▲)



            var ax:Number = this.mW - 26;



            var ay:Number = Math.floor(this.mBarH / 2);



            this.mArrow.graphics.lineStyle(2, 0xFFFFFF, 1.0, true);



            this.mArrow.graphics.moveTo(ax - 5, ay + 2);



            this.mArrow.graphics.lineTo(ax, ay - 3);



            this.mArrow.graphics.lineTo(ax + 5, ay + 2);



        }



        else



        {



            // === СВЕРНУТО: Серебристо-серый градиент ===



            this.mBg.graphics.beginFill(0x000000, 0.04);



            this.mBg.graphics.drawRoundRect(0, 2, this.mW, this.mBarH, 6, 6);



            this.mBg.graphics.endFill();



            var borderCol:uint = this.mHover ? 0x4B87C2 : 0xB8C5D3;



            this.mBg.graphics.beginFill(borderCol, 1.0);



            this.mBg.graphics.drawRoundRect(0, 0, this.mW, this.mBarH, 6, 6);



            this.mBg.graphics.endFill();



            var topCol:uint = this.mHover ? 0xF8FAFD : 0xF2F6FA;



            var botCol:uint = this.mHover ? 0xDCE6F0 : 0xD5E0EC;



            this.mBg.graphics.beginGradientFill(



                GradientType.LINEAR,



                [topCol, botCol],



                [1.0, 1.0],



                [0, 255],



                bMat



            );



            this.mBg.graphics.drawRoundRect(1, 1, this.mW - 2, this.mBarH - 2, 5, 5);



            this.mBg.graphics.endFill();



            this.mTf.textColor = this.mHover ? 0x0B65A8 : SettingsUI.COL_ROYAL_BLUE;



            // Стрелочка ВНИЗ (▼)



            var ax2:Number = this.mW - 26;



            var ay2:Number = Math.floor(this.mBarH / 2);



            var arrowCol:uint = this.mHover ? 0x0B65A8 : SettingsUI.COL_ROYAL_BLUE;



            this.mArrow.graphics.lineStyle(2, arrowCol, 1.0, true);



            this.mArrow.graphics.moveTo(ax2 - 5, ay2 - 2);



            this.mArrow.graphics.lineTo(ax2, ay2 + 3);



            this.mArrow.graphics.lineTo(ax2 + 5, ay2 - 2);



        }



    }



}



class MaxisScrollView extends Sprite



{



    private var mW:Number;



    private var mH:Number;



    private var mContent:Sprite = new Sprite();



    private var mHitArea:Shape = new Shape();



    private var mTrack:Sprite = new Sprite();



    private var mThumb:Sprite = new Sprite();



    private var mThumbH:Number = 30;



    private var mTrackW:Number = 10;



    private var mScrollY:Number = 0;



    private var mMaxScroll:Number = 0;



    private var mTotalContentH:Number = 0;



    private var mIsDragging:Boolean = false;



    private var mDragStartY:Number = 0;



    private var mThumbStartY:Number = 0;



    private var mIsHovered:Boolean = false;



    private var mOwnerSections:Array = null;



    public function MaxisScrollView(w:Number, h:Number)



    {



        this.mW = w;



        this.mH = h;



        this.scrollRect = new Rectangle(0, 0, mW, mH);



        // Невидимый слой для захвата событий мыши и колесика на всей области скролла



        mHitArea.graphics.beginFill(0xFFFFFF, 0);



        mHitArea.graphics.drawRect(0, 0, mW, mH);



        mHitArea.graphics.endFill();



        addChild(mHitArea);



        // Контейнер контента



        addChild(mContent);



        // Скроллбар справа



        var trackX:Number = mW - mTrackW;



        mTrack.x = trackX;



        mTrack.y = 0;



        mTrack.buttonMode = true;



        addChild(mTrack);



        mThumb.x = trackX;



        mThumb.y = 0;



        mThumb.buttonMode = true;



        mThumb.useHandCursor = true;



        addChild(mThumb);



        drawTrack();



        drawThumb(false, false);



        // Слушатели колесика мыши



        addEventListener(MouseEvent.MOUSE_WHEEL, onMouseWheel);



        // Слушатели трека



        mTrack.addEventListener(MouseEvent.CLICK, onTrackClick);



        // Слушатели ползунка



        mThumb.addEventListener(MouseEvent.ROLL_OVER, onThumbOver);



        mThumb.addEventListener(MouseEvent.ROLL_OUT, onThumbOut);



        mThumb.addEventListener(MouseEvent.MOUSE_DOWN, onThumbDown);



        updateLayout(0);



    }



    public function setOwnerSections(secs:Array):void



    {



        this.mOwnerSections = secs;



    }



    public function getContent():Sprite



    {



        return mContent;



    }



    public function getViewportWidth():Number



    {



        return mW - mTrackW - 6;



    }



    public function getViewportHeight():Number



    {



        return mH;



    }



    public function getScrollY():Number



    {



        return mScrollY;



    }



    public function resetScroll():void



    {



        mScrollY = 0;



        applyScroll();



        updateThumbPosition();



    }



    public function scrollTo(targetY:Number):void



    {



        mScrollY = targetY;



        if (mScrollY < 0) mScrollY = 0;



        if (mScrollY > mMaxScroll) mScrollY = mMaxScroll;



        applyScroll();



        updateThumbPosition();



    }



    public function updateLayout(explicitContentH:Number = -1):void



    {



        this.scrollRect = new Rectangle(0, 0, mW, mH);



        var contentH:Number = (explicitContentH >= 0) ? explicitContentH : mContent.height;



        this.mTotalContentH = contentH;



        if (contentH <= mH)



        {



            mMaxScroll = 0;



            mScrollY = 0;



            mTrack.visible = false;



            mThumb.visible = false;



        }



        else



        {



            mMaxScroll = contentH - mH;



            if (mScrollY > mMaxScroll) mScrollY = mMaxScroll;



            mTrack.visible = true;



            mThumb.visible = true;



            mThumbH = Math.max(28, Math.round((mH / contentH) * mH));



            drawThumb(mIsHovered, mIsDragging);



            updateThumbPosition();



        }



        applyScroll();



    }



    private function applyScroll():void



    {



        mContent.y = -Math.round(mScrollY);



        // Виртуальное клиппирование строк и заголовков



        if (this.mOwnerSections != null)



        {



            for (var i:int = 0; i < this.mOwnerSections.length; i++)



            {



                var sec:MaxisAccordionSection = this.mOwnerSections[i] as MaxisAccordionSection;



                if (sec != null)



                {



                    sec.clipToViewport(mScrollY, mH);



                }



            }



        }



    }



    private function updateThumbPosition():void



    {



        var maxThumbY:Number = mH - mThumbH;



        if (mMaxScroll > 0 && maxThumbY > 0)



        {



            var ratio:Number = mScrollY / mMaxScroll;



            mThumb.y = Math.round(ratio * maxThumbY);



        }



        else



        {



            mThumb.y = 0;



        }



    }



    private function drawTrack():void



    {



        mTrack.graphics.clear();



        mTrack.graphics.beginFill(0xBAC5D4, 0.35);



        mTrack.graphics.drawRoundRect(0, 0, mTrackW, mH, 8, 8);



        mTrack.graphics.endFill();



    }



    private function drawThumb(isHover:Boolean, isDown:Boolean):void



    {



        mThumb.graphics.clear();



        var mat:Matrix = new Matrix();



        mat.createGradientBox(mTrackW, mThumbH, Math.PI / 2, 0, 0);



        var colTop:uint = 0xDEE5ED;



        var colBottom:uint = 0xB5C2D0;



        var borderCol:uint = 0x8C9DAC;



        if (isDown)



        {



            colTop = 0xADC0D3;



            colBottom = 0x8DA2B8;



            borderCol = 0x487AA8;



        }



        else if (isHover)



        {



            colTop = 0xEFF4FA;



            colBottom = 0xC8D4E2;



            borderCol = 0x5C8EBD;



        }



        mThumb.graphics.lineStyle(1, borderCol, 0.85, true);



        mThumb.graphics.beginGradientFill(GradientType.LINEAR, [colTop, colBottom], [1, 1], [0, 255], mat);



        mThumb.graphics.drawRoundRect(0, 0, mTrackW, mThumbH, 8, 8);



        mThumb.graphics.endFill();



    }



    private function onThumbOver(e:MouseEvent):void



    {



        mIsHovered = true;



        if (!mIsDragging) drawThumb(true, false);



    }



    private function onThumbOut(e:MouseEvent):void



    {



        mIsHovered = false;



        if (!mIsDragging) drawThumb(false, false);



    }



    private function onThumbDown(e:MouseEvent):void



    {



        if (stage == null) return;



        mIsDragging = true;



        mDragStartY = stage.mouseY;



        mThumbStartY = mThumb.y;



        stage.addEventListener(MouseEvent.MOUSE_MOVE, onStageMouseMove);



        stage.addEventListener(MouseEvent.MOUSE_UP, onStageMouseUp);



        drawThumb(mIsHovered, true);



        e.stopPropagation();



    }



    private function onStageMouseMove(e:MouseEvent):void



    {



        if (!mIsDragging) return;



        var maxThumbY:Number = mH - mThumbH;



        if (maxThumbY <= 0) return;



        var dy:Number = stage.mouseY - mDragStartY;



        var newY:Number = mThumbStartY + dy;



        if (newY < 0) newY = 0;



        if (newY > maxThumbY) newY = maxThumbY;



        mThumb.y = newY;



        var ratio:Number = newY / maxThumbY;



        mScrollY = ratio * mMaxScroll;



        applyScroll();



    }



    private function onStageMouseUp(e:MouseEvent):void



    {



        if (!mIsDragging) return;



        mIsDragging = false;



        if (stage != null)



        {



            stage.removeEventListener(MouseEvent.MOUSE_MOVE, onStageMouseMove);



            stage.removeEventListener(MouseEvent.MOUSE_UP, onStageMouseUp);



        }



        drawThumb(mIsHovered, false);



    }



    private function onTrackClick(e:MouseEvent):void



    {



        var clickY:Number = e.localY;



        var maxThumbY:Number = mH - mThumbH;



        if (maxThumbY <= 0) return;



        var targetThumbY:Number = clickY - (mThumbH / 2);



        if (targetThumbY < 0) targetThumbY = 0;



        if (targetThumbY > maxThumbY) targetThumbY = maxThumbY;



        mThumb.y = targetThumbY;



        var ratio:Number = targetThumbY / maxThumbY;



        mScrollY = ratio * mMaxScroll;



        applyScroll();



    }



    private function onMouseWheel(e:MouseEvent):void



    {



        if (mMaxScroll <= 0) return;



        var step:Number = 36;



        var targetY:Number = mScrollY - (e.delta * step);



        if (targetY < 0) targetY = 0;



        if (targetY > mMaxScroll) targetY = mMaxScroll;



        mScrollY = targetY;



        applyScroll();



        updateThumbPosition();



        e.stopPropagation();



    }



}



class SimsCheckbox extends Sprite



{



    private var mKey:String;



    private var mState:Boolean;



    private var mHover:Boolean = false;



    private var mBox:Shape = new Shape();



    private var mCheck:Shape = new Shape();



    private var mCallback:Function;



    public function SimsCheckbox(key:String, initial:Boolean, callback:Function = null)



    {



        super();



        this.mKey = key;



        this.mState = initial;



        this.mCallback = callback;



        this.buttonMode = true;



        this.useHandCursor = true;



        this.mouseChildren = false;



        // Невидимый прозрачный слой 24x24 для 100% надёжного клика



        this.graphics.beginFill(0xFFFFFF, 0.001);



        this.graphics.drawRect(-2, -2, 24, 24);



        this.graphics.endFill();



        addChild(this.mBox);



        addChild(this.mCheck);



        this.redraw();



        addEventListener(MouseEvent.ROLL_OVER, this.onOver);



        addEventListener(MouseEvent.ROLL_OUT, this.onOut);



        addEventListener(MouseEvent.CLICK, this.onToggle);



    }



    public function setState(val:Boolean):void



    {



        this.mState = val;



        this.redraw();



    }



    public function getState():Boolean



    {



        return this.mState;



    }



    private function onOver(e:MouseEvent):void



    {



        this.mHover = true;



        this.redraw();



    }



    private function onOut(e:MouseEvent):void



    {



        this.mHover = false;



        this.redraw();



    }



    private function onToggle(e:MouseEvent):void



    {



        e.stopPropagation();



        this.mState = !this.mState;



        this.redraw();



        if (this.mCallback != null)



        {



            this.mCallback(this.mKey, this.mState);



        }



        else



        {



            SettingsUI.sendSetting(this.mKey, this.mState);



        }



    }



    private function redraw():void



    {



        this.mBox.graphics.clear();



        this.mCheck.graphics.clear();



        // 1. Векторная многослойная падающая тень снизу



        this.mBox.graphics.beginFill(0x000000, 0.05);



        this.mBox.graphics.drawRoundRect(0, 3, 20, 20, 8, 8);



        this.mBox.graphics.endFill();



        this.mBox.graphics.beginFill(0x000000, 0.13);



        this.mBox.graphics.drawRoundRect(0, 2, 20, 20, 8, 8);



        this.mBox.graphics.endFill();



        this.mBox.graphics.beginFill(0x000000, 0.24);



        this.mBox.graphics.drawRoundRect(0, 1, 20, 20, 8, 8);



        this.mBox.graphics.endFill();



        var bMat:Matrix = new Matrix();



        bMat.createGradientBox(20, 20, Math.PI / 2, 0, 0);



        var mat:Matrix = new Matrix();



        mat.createGradientBox(18, 17, Math.PI / 2, 1, 2);



        if (this.mState)



        {



            // 2. Внешний 3D-контур зелёного чекбокса



            this.mBox.graphics.beginGradientFill(



                GradientType.LINEAR,



                [0x639D44, 0x2D9139, 0x3D6E42],



                [1.0, 1.0, 1.0],



                [0, 180, 255],



                bMat



            );



            this.mBox.graphics.drawRoundRect(0, 0, 20, 20, 7, 7);



            this.mBox.graphics.endFill();



            // 3. Верхний светло-зелёный 1px блик



            this.mBox.graphics.beginFill(this.mHover ? 0x82DA46 : 0x6EC635, 1.0);



            this.mBox.graphics.drawRoundRect(1, 1, 18, 17, 5, 5);



            this.mBox.graphics.endFill();



            // 4. Внутренний выпуклый зелёный градиент



            var gTop:uint = this.mHover ? 0x6CC832 : 0x5EB626;



            var gMid:uint = this.mHover ? 0x55B824 : 0x4DB325;



            var gBot:uint = this.mHover ? 0x2CAE36 : 0x23A02E;



            this.mBox.graphics.beginGradientFill(



                GradientType.LINEAR,



                [gTop, gMid, gBot],



                [1.0, 1.0, 1.0],



                [0, 135, 255],



                mat



            );



            this.mBox.graphics.drawRoundRect(1, 2, 18, 16, 5, 5);



            this.mBox.graphics.endFill();



            // 5. Тень под галочкой + белая галочка



            this.mCheck.graphics.lineStyle(2.4, 0x1D7A22, 0.55);



            this.mCheck.graphics.moveTo(5, 11);



            this.mCheck.graphics.lineTo(8.5, 15);



            this.mCheck.graphics.lineTo(15, 6.5);



            this.mCheck.graphics.lineStyle(2.4, 0xFFFFFF, 1.0);



            this.mCheck.graphics.moveTo(5, 10);



            this.mCheck.graphics.lineTo(8.5, 14);



            this.mCheck.graphics.lineTo(15, 5.5);



        }



        else



        {



            // 2. Внешний 3D-контур пустого чекбокса



            this.mBox.graphics.beginGradientFill(



                GradientType.LINEAR,



                [0xD4D4D4, 0xB8B8B8, 0x9C9D9E],



                [1.0, 1.0, 1.0],



                [0, 180, 255],



                bMat



            );



            this.mBox.graphics.drawRoundRect(0, 0, 20, 20, 7, 7);



            this.mBox.graphics.endFill();



            // 3. Внутренний верхний 1px световой блик



            this.mBox.graphics.beginFill(0xFFFFFF, 1.0);



            this.mBox.graphics.drawRoundRect(1, 1, 18, 17, 5, 5);



            this.mBox.graphics.endFill();



            // 4. Внутренний гладкий серебристый градиент



            var sTop:uint = this.mHover ? 0xFFFFFF : 0xF4F4F4;



            var sMid:uint = this.mHover ? 0xEFEFEF : 0xE6E6E6;



            var sBot:uint = this.mHover ? 0xDCDCDC : 0xD1D1D1;



            this.mBox.graphics.beginGradientFill(



                GradientType.LINEAR,



                [sTop, sMid, sBot],



                [1.0, 1.0, 1.0],



                [0, 140, 255],



                mat



            );



            this.mBox.graphics.drawRoundRect(1, 2, 18, 16, 5, 5);



            this.mBox.graphics.endFill();



        }



    }



}



class SimsDropdown extends Sprite



{



    private var mKey:String;



    private var mOptions:Array;



    private var mIndex:int;



    private var mHoverIndex:int = -1;



    private var mW:Number;



    private var mH:Number;



    private var mOwner:SettingsUI;



    private var mHover:Boolean = false;



    private var mOpen:Boolean = false;



    private var mHeaderBtn:Sprite = new Sprite();



    private var mBg:Shape = new Shape();



    private var mArrow:Shape = new Shape();



    private var mLabel:TextField;



    private var mPopup:Sprite = new Sprite();



    private var mRowBgs:Array = [];



    private var mRowTfs:Array = [];



    public function SimsDropdown(key:String, options:Array, initialIndex:int, w:Number, h:Number, owner:SettingsUI)



    {



        super();



        this.mKey = key;



        this.mOptions = options;



        this.mIndex = initialIndex;



        this.mW = w;



        this.mH = h;



        this.mOwner = owner;



        this.mHeaderBtn.buttonMode = true;



        this.mHeaderBtn.mouseChildren = false;



        this.mHeaderBtn.addChild(this.mBg);



        this.mHeaderBtn.addChild(this.mArrow);



        var initialText:String = (this.mOptions.length > 0) ? String(this.mOptions[this.mIndex]) : "";



        this.mLabel = SettingsUI.makeText(initialText, 13, SettingsUI.COL_ROYAL_BLUE);



        this.mLabel.x = 10;



        this.mLabel.y = 4;



        this.mHeaderBtn.addChild(this.mLabel);



        addChild(this.mHeaderBtn);



        this.mPopup.visible = false;



        addChild(this.mPopup);



        this.buildPopupRows();



        this.redraw();



        this.mHeaderBtn.addEventListener(MouseEvent.ROLL_OVER, this.onOver);



        this.mHeaderBtn.addEventListener(MouseEvent.ROLL_OUT, this.onOut);



        this.mHeaderBtn.addEventListener(MouseEvent.MOUSE_DOWN, this.onHeaderMouseDown);



    }



    private function buildPopupRows():void



    {



        while (this.mPopup.numChildren > 0)



        {



            this.mPopup.removeChildAt(0);



        }



        this.mRowBgs = [];



        this.mRowTfs = [];



        var itemH:Number = 24;



        for (var i:int = 0; i < this.mOptions.length; i++)



        {



            var row:Sprite = new Sprite();



            row.name = String(i);



            row.x = 2;



            row.y = this.mH + 2 + i * itemH;



            row.buttonMode = true;



            row.mouseChildren = false;



            var rBg:Shape = new Shape();



            row.addChild(rBg);



            var rTf:TextField = SettingsUI.makeText(String(this.mOptions[i]), 13, SettingsUI.COL_ROYAL_BLUE);



            rTf.x = 8;



            rTf.y = 2;



            row.addChild(rTf);



            row.addEventListener(MouseEvent.ROLL_OVER, this.onRowOver);



            row.addEventListener(MouseEvent.ROLL_OUT, this.onRowOut);



            row.addEventListener(MouseEvent.MOUSE_DOWN, this.onRowDown);



            this.mPopup.addChild(row);



            this.mRowBgs.push(rBg);



            this.mRowTfs.push(rTf);



        }



        this.refreshRows();



    }



    private function onRowOver(e:MouseEvent):void



    {



        var sp:Sprite = e.currentTarget as Sprite;



        if (sp != null)



        {



            this.mHoverIndex = int(sp.name);



            this.refreshRows();



        }



    }



    private function onRowOut(e:MouseEvent):void



    {



        this.mHoverIndex = -1;



        this.refreshRows();



    }



    private function onRowDown(e:MouseEvent):void



    {



        e.stopPropagation();



        var sp:Sprite = e.currentTarget as Sprite;



        if (sp != null)



        {



            this.selectOption(int(sp.name));



        }



    }



    private function onOver(e:MouseEvent):void



    {



        this.mHover = true;



        this.redraw();



    }



    private function onOut(e:MouseEvent):void



    {



        this.mHover = false;



        this.redraw();



    }



    private function onHeaderMouseDown(e:MouseEvent):void



    {



        e.stopPropagation();



        if (this.mOpen)



        {



            if (this.mOwner != null)



            {



                this.mOwner.closeActivePopup();



            }



            else



            {



                this.closePopup();



            }



        }



        else



        {



            if (this.mOwner != null)



            {



                this.mOwner.closeActivePopup();



                this.mOwner.setOpenDropdown(this);



            }



            this.mOpen = true;



            this.mHoverIndex = -1;



            try



            {



                if (this.parent)



                {



                    this.parent.setChildIndex(this, this.parent.numChildren - 1);



                }



            }



            catch (errZ2:Error) {}



            this.mPopup.visible = true;



            this.refreshRows();



            this.redraw();



        }



    }



    public function closePopup():void



    {



        this.mOpen = false;



        this.mHoverIndex = -1;



        if (this.mPopup)



        {



            this.mPopup.visible = false;



        }



        this.redraw();



    }



    public function selectOption(idx:int):void



    {



        if (idx >= 0 && idx < this.mOptions.length)



        {



            this.mIndex = idx;



            var val:String = String(this.mOptions[this.mIndex]);



            this.mLabel.text = val;



            SettingsUI.sendSetting(this.mKey, val);



        }



        if (this.mOwner != null)



        {



            this.mOwner.closeActivePopup();



        }



        else



        {



            this.closePopup();



        }



    }



    private function refreshRows():void



    {



        var itemH:Number = 24;



        var rowW:Number = this.mW - 4;



        for (var i:int = 0; i < this.mRowBgs.length; i++)



        {



            var rBg:Shape = this.mRowBgs[i] as Shape;



            var rTf:TextField = this.mRowTfs[i] as TextField;



            var isHov:Boolean = (i == this.mHoverIndex);



            var isSel:Boolean = (i == this.mIndex);



            if (rBg != null)



            {



                rBg.graphics.clear();



                rBg.graphics.beginFill(isHov ? 0xF2F6FA : 0xFFFFFF, 1.0);



                rBg.graphics.drawRoundRect(0, 0, rowW, itemH, 4, 4);



                rBg.graphics.endFill();



            }



            if (rTf != null)



            {



                var highlightRow:Boolean = false;



                if (isSel)



                {



                    highlightRow = true;



                }



                else if (isHov)



                {



                    highlightRow = true;



                }



                rTf.textColor = highlightRow ? SettingsUI.COL_HOVER_GREEN : SettingsUI.COL_ROYAL_BLUE;



            }



        }



    }



    private function redraw():void



    {



        this.mBg.graphics.clear();



        var isHighlighted:Boolean = false;



        if (this.mHover)



        {



            isHighlighted = true;



        }



        else if (this.mOpen)



        {



            isHighlighted = true;



        }



        this.mLabel.textColor = isHighlighted ? SettingsUI.COL_HOVER_GREEN : SettingsUI.COL_ROYAL_BLUE;



        if (this.mOpen)



        {



            // Раскрытая карточка списка (единый белый блок от верха контрола до конца всех пунктов, как на видео OBS!)



            var itemH:Number = 24;



            var totalH:Number = this.mH + this.mOptions.length * itemH + 6;



            // Многослойная 3D-тень вокруг раскрытого меню



            this.mBg.graphics.beginFill(0x000000, 0.05);



            this.mBg.graphics.drawRoundRect(-1, 5, this.mW + 2, totalH, 10, 10);



            this.mBg.graphics.endFill();



            this.mBg.graphics.beginFill(0x000000, 0.12);



            this.mBg.graphics.drawRoundRect(0, 3, this.mW, totalH, 9, 9);



            this.mBg.graphics.endFill();



            this.mBg.graphics.beginFill(0x000000, 0.22);



            this.mBg.graphics.drawRoundRect(0, 1, this.mW, totalH, 9, 9);



            this.mBg.graphics.endFill();



            // Внешняя рамка раскрытого списка (#C7C7C7 сверху -> #9A9A9A снизу)



            var openBMat:Matrix = new Matrix();



            openBMat.createGradientBox(this.mW, totalH, Math.PI / 2, 0, 0);



            this.mBg.graphics.beginGradientFill(



                GradientType.LINEAR,



                [0xC7C7C7, 0xB0B0B0, 0x969696],



                [1.0, 1.0, 1.0],



                [0, 180, 255],



                openBMat



            );



            this.mBg.graphics.drawRoundRect(0, 0, this.mW, totalH, 9, 9);



            this.mBg.graphics.endFill();



            // Чисто-белое внутреннее полотно раскрытого списка (#FFFFFF)



            this.mBg.graphics.beginFill(0xFFFFFF, 1.0);



            this.mBg.graphics.drawRoundRect(1, 1, this.mW - 2, totalH - 2, 7, 7);



            this.mBg.graphics.endFill();



            // Тонкая разделительная линия под шапкой списка



            this.mBg.graphics.beginFill(0xE4E8EE, 1.0);



            this.mBg.graphics.drawRect(2, this.mH - 1, this.mW - 4, 1);



            this.mBg.graphics.endFill();



        }



        else



        {



            // 1. Многослойная векторная тень снизу (#FBFBFB -> #F2F2F2 -> #DBDBDB -> #AEAEAE из попиксельного скана IMG1)



            this.mBg.graphics.beginFill(0x000000, 0.04);



            this.mBg.graphics.drawRoundRect(0, 4, this.mW, this.mH, 9, 9);



            this.mBg.graphics.endFill();



            this.mBg.graphics.beginFill(0x000000, 0.10);



            this.mBg.graphics.drawRoundRect(0, 3, this.mW, this.mH, 9, 9);



            this.mBg.graphics.endFill();



            this.mBg.graphics.beginFill(0x000000, 0.19);



            this.mBg.graphics.drawRoundRect(0, 2, this.mW, this.mH, 9, 9);



            this.mBg.graphics.endFill();



            this.mBg.graphics.beginFill(0x000000, 0.30);



            this.mBg.graphics.drawRoundRect(0, 1, this.mW, this.mH, 9, 9);



            this.mBg.graphics.endFill();



            // 2. Внешний 3D-корпус рамки (#C7C7C7 сверху -> #B4B4B4 по бокам -> #8E8E8E снизу, без синей обводки!)



            var bMat:Matrix = new Matrix();



            bMat.createGradientBox(this.mW, this.mH, Math.PI / 2, 0, 0);



            this.mBg.graphics.beginGradientFill(



                GradientType.LINEAR,



                [0xC7C7C7, 0xB4B4B4, 0x8E8E8E],



                [1.0, 1.0, 1.0],



                [0, 175, 255],



                bMat



            );



            this.mBg.graphics.drawRoundRect(0, 0, this.mW, this.mH, 9, 9);



            this.mBg.graphics.endFill();



            // 3. Верхний 1px чисто-белый блик (#FFFFFF)



            this.mBg.graphics.beginFill(0xFFFFFF, 1.0);



            this.mBg.graphics.drawRoundRect(1, 1, this.mW - 2, this.mH - 2, 7, 7);



            this.mBg.graphics.endFill();



            // 4. Выпуклый серебристо-белый градиент (при наведении мягко белеет, как на записи OBS!)



            var mat:Matrix = new Matrix();



            mat.createGradientBox(this.mW - 2, this.mH - 3, Math.PI / 2, 1, 2);



            var topC:uint = 0xFFFFFF;



            var midC:uint = this.mHover ? 0xFCFCFC : 0xEFEFEF;



            var botC:uint = this.mHover ? 0xF2F2F2 : 0xDEDEDE;



            this.mBg.graphics.beginGradientFill(



                GradientType.LINEAR,



                [topC, midC, botC],



                [1.0, 1.0, 1.0],



                [0, 135, 255],



                mat



            );



            this.mBg.graphics.drawRoundRect(1, 2, this.mW - 2, this.mH - 3, 7, 7);



            this.mBg.graphics.endFill();



        }



        // 5. Треугольник справа (▼ в закрытом виде, ▲ в открытом, зелёный при наведении/открытии!)



        this.mArrow.graphics.clear();



        var ax:Number = this.mW - 15;



        var ay:Number = Math.round(this.mH * 0.5) - 2;



        var arrowCol:uint = isHighlighted ? SettingsUI.COL_HOVER_GREEN : SettingsUI.COL_ROYAL_BLUE;



        this.mArrow.graphics.beginFill(arrowCol, 1.0);



        if (this.mOpen)



        {



            this.mArrow.graphics.moveTo(ax - 5, ay + 5);



            this.mArrow.graphics.lineTo(ax + 5, ay + 5);



            this.mArrow.graphics.lineTo(ax, ay - 0.5);



            this.mArrow.graphics.lineTo(ax - 5, ay + 5);



        }



        else



        {



            this.mArrow.graphics.moveTo(ax - 5, ay);



            this.mArrow.graphics.lineTo(ax + 5, ay);



            this.mArrow.graphics.lineTo(ax, ay + 5.5);



            this.mArrow.graphics.lineTo(ax - 5, ay);



        }



        this.mArrow.graphics.endFill();



    }



}



// =========================================================================



// 3D-ПОЛЗУНОК В СТИЛЕ SIMS 4 (ОБЪЁМНЫЙ БЕГУНОК С ТЕНЬЮ, БЕЗ lineStyle)



// =========================================================================



class SimsSlider extends Sprite



{



    private var mKey:String;



    private var mMin:Number;



    private var mMax:Number;



    private var mVal:Number;



    private var mTrackW:Number;



    private var mOwner:SettingsUI;



    private var mTrackBg:Shape = new Shape();



    private var mFillBar:Shape = new Shape();



    private var mThumb:Sprite = new Sprite();



    private var mLabel:TextField;



    private var mDragging:Boolean = false;



    public function SimsSlider(key:String, min:Number, max:Number, initial:Number, trackW:Number, owner:SettingsUI)



    {



        super();



        this.mKey = key;



        this.mMin = min;



        this.mMax = max;



        this.mVal = initial;



        this.mTrackW = trackW;



        this.mOwner = owner;



        this.buttonMode = true;



        addChild(this.mTrackBg);



        addChild(this.mFillBar);



        // Объёмный 3D-бегунок с векторной тенью (без lineStyle и без DropShadowFilter)



        this.mThumb.graphics.beginFill(0x000000, 0.10);



        this.mThumb.graphics.drawCircle(0, 2.5, 8.5);



        this.mThumb.graphics.endFill();



        this.mThumb.graphics.beginFill(0x000000, 0.24);



        this.mThumb.graphics.drawCircle(0, 1.5, 8.2);



        this.mThumb.graphics.endFill();



        var bMat:Matrix = new Matrix();



        bMat.createGradientBox(16, 16, Math.PI / 2, -8, -8);



        this.mThumb.graphics.beginGradientFill(GradientType.LINEAR, [0xC7C7C7, 0x828282], [1.0, 1.0], [0, 255], bMat);



        this.mThumb.graphics.drawCircle(0, 0, 8);



        this.mThumb.graphics.endFill();



        this.mThumb.graphics.beginFill(0xFFFFFF, 1.0);



        this.mThumb.graphics.drawCircle(0, -0.4, 7);



        this.mThumb.graphics.endFill();



        var tMat:Matrix = new Matrix();



        tMat.createGradientBox(14, 14, Math.PI / 2, -7, -6.5);



        this.mThumb.graphics.beginGradientFill(GradientType.LINEAR, [0xFEFEFE, 0xEDEDED, 0xDADADA], [1.0, 1.0, 1.0], [0, 140, 255], tMat);



        this.mThumb.graphics.drawCircle(0, 0, 6.8);



        this.mThumb.graphics.endFill();



        addChild(this.mThumb);



        this.mLabel = SettingsUI.makeText("", 13, SettingsUI.COL_ROYAL_BLUE);



        this.mLabel.x = this.mTrackW + 10;



        this.mLabel.y = -10;



        addChild(this.mLabel);



        this.updateVisuals();



        addEventListener(MouseEvent.MOUSE_DOWN, this.onDown);



        if (stage)



        {



            this.onSliderAdded(null);



        }



        else



        {



            addEventListener(Event.ADDED_TO_STAGE, this.onSliderAdded);



        }



    }



    private function onSliderAdded(e:Event):void



    {



        removeEventListener(Event.ADDED_TO_STAGE, this.onSliderAdded);



        if (stage)



        {



            stage.addEventListener(MouseEvent.MOUSE_MOVE, this.onMove);



            stage.addEventListener(MouseEvent.MOUSE_UP, this.onUp);



        }



    }



    private function onDown(e:MouseEvent):void



    {



        if (this.mOwner != null)



        {



            this.mOwner.closeActivePopup();



        }



        this.mDragging = true;



        this.updateFromMouse();



    }



    private function onMove(e:MouseEvent):void



    {



        if (this.mDragging)



        {



            this.updateFromMouse();



        }



    }



    private function onUp(e:MouseEvent):void



    {



        if (this.mDragging)



        {



            this.mDragging = false;



            SettingsUI.sendSetting(this.mKey, this.mVal);



        }



    }



    private function updateFromMouse():void



    {



        var ratio:Number = Math.max(0, Math.min(1, this.mouseX / this.mTrackW));



        this.mVal = Math.round(this.mMin + ratio * (this.mMax - this.mMin));



        this.updateVisuals();



    }



    private function updateVisuals():void



    {



        var ratio:Number = (this.mVal - this.mMin) / (this.mMax - this.mMin);



        var fillW:Number = ratio * this.mTrackW;



        // Вдавленный 3D-жёлоб ползунка (тёмный верх #9E9E9E, светлый низ #F2F2F2)



        this.mTrackBg.graphics.clear();



        this.mTrackBg.graphics.beginFill(0x9E9E9E, 1.0);



        this.mTrackBg.graphics.drawRoundRect(0, -4, this.mTrackW, 8, 8, 8);



        this.mTrackBg.graphics.endFill();



        this.mTrackBg.graphics.beginFill(0xDDDDDD, 1.0);



        this.mTrackBg.graphics.drawRoundRect(1, -3, this.mTrackW - 2, 7, 6, 6);



        this.mTrackBg.graphics.endFill();



        this.mTrackBg.graphics.beginFill(0xEAEAEA, 1.0);



        this.mTrackBg.graphics.drawRoundRect(1, -2, this.mTrackW - 2, 5, 5, 5);



        this.mTrackBg.graphics.endFill();



        this.mFillBar.graphics.clear();



        if (fillW > 2)



        {



            var fMat:Matrix = new Matrix();



            fMat.createGradientBox(Math.max(6, fillW), 6, Math.PI / 2, 1, -3);



            this.mFillBar.graphics.beginGradientFill(GradientType.LINEAR, [0x66C628, 0x359E16], [1.0, 1.0], [0, 255], fMat);



            this.mFillBar.graphics.drawRoundRect(1, -3, Math.max(6, fillW), 6, 6, 6);



            this.mFillBar.graphics.endFill();



        }



        this.mThumb.x = fillW;



        this.mLabel.text = String(this.mVal) + " м";



    }



}



// =========================================================================



// КАПСУЛЬНАЯ 3D-КНОПКА SIMS 4 (ТОЧНАЯ КОПИЯ С ГЛУБОКИМ НИЖНИМ 3D-СКОСОМ)



// =========================================================================



class SimsPillButton extends Sprite



{



    private var mW:Number;



    private var mH:Number;



    private var mKey:String;



    private var mVal:String;



    private var mOwner:SettingsUI;



    private var mCloseOnClick:Boolean;



    private var mBg:Shape = new Shape();



    private var mTf:TextField;



    public function SimsPillButton(text:String, w:Number, h:Number, key:String, val:String, owner:SettingsUI, closeOnClick:Boolean = false, fontSize:int = 13)



    {



        super();



        this.mW = w;



        this.mH = h;



        this.mKey = key;



        this.mVal = val;



        this.mOwner = owner;



        this.mCloseOnClick = closeOnClick;



        this.buttonMode = true;



        this.mouseChildren = false;



        addChild(this.mBg);



        this.mTf = SettingsUI.makeCenteredText(text, fontSize, SettingsUI.COL_ROYAL_BLUE, w);



        this.mTf.x = 0;



        this.mTf.y = Math.max(2, Math.floor((h - (fontSize + 8)) / 2));



        addChild(this.mTf);



        this.draw(false);



        addEventListener(MouseEvent.ROLL_OVER, this.onOver);



        addEventListener(MouseEvent.ROLL_OUT, this.onOut);



        addEventListener(MouseEvent.CLICK, this.onClick);



    }



    private function onOver(e:MouseEvent):void



    {



        this.draw(true);



    }



    private function onOut(e:MouseEvent):void



    {



        this.draw(false);



    }



    private function onClick(e:MouseEvent):void



    {



        if (this.mOwner != null)



        {



            this.mOwner.closeActivePopup();



        }



        if (this.mKey && this.mKey.length > 0 && this.mKey != "custom_action")



        {



            SettingsUI.sendSetting(this.mKey, this.mVal);



        }



        if (this.mCloseOnClick && this.mOwner != null)



        {



            this.mOwner.setModal(false);



        }



    }



    private var mSelected:Boolean = false;



    public function setSelected(val:Boolean):void



    {



        this.mSelected = val;



        this.draw(false);



    }



    private function draw(hover:Boolean):void



    {



        this.mBg.graphics.clear();



        if (this.mSelected)



        {



            if (this.mTf != null) this.mTf.textColor = 0xFFFFFF;



            this.mBg.graphics.beginFill(0x000000, 0.08);



            this.mBg.graphics.drawRoundRect(0, 2, this.mW, this.mH, this.mH, this.mH);



            this.mBg.graphics.endFill();



            var bMatS:Matrix = new Matrix();



            bMatS.createGradientBox(this.mW, this.mH, Math.PI / 2, 0, 0);



            this.mBg.graphics.beginGradientFill(



                GradientType.LINEAR,



                [0x68C430, 0x429D1E, 0x24780E],



                [1.0, 1.0, 1.0],



                [0, 160, 255],



                bMatS



            );



            this.mBg.graphics.drawRoundRect(0, 0, this.mW, this.mH, this.mH, this.mH);



            this.mBg.graphics.endFill();



            this.mBg.graphics.beginFill(0xFFFFFF, hover ? 0.40 : 0.25);



            this.mBg.graphics.drawRoundRect(1, 1, this.mW - 2, Math.floor(this.mH / 2), this.mH - 2, this.mH - 2);



            this.mBg.graphics.endFill();



            return;



        }



        if (this.mTf != null)



        {



            this.mTf.textColor = hover ? SettingsUI.COL_HOVER_GREEN : SettingsUI.COL_ROYAL_BLUE;



        }



        // 1. Мягкая векторная падающая тень снизу капсулы



        this.mBg.graphics.beginFill(0x000000, 0.06);



        this.mBg.graphics.drawRoundRect(0, 2, this.mW, this.mH, this.mH, this.mH);



        this.mBg.graphics.endFill();



        this.mBg.graphics.beginFill(0x000000, 0.10);



        this.mBg.graphics.drawRoundRect(0, 1, this.mW, this.mH, this.mH, this.mH);



        this.mBg.graphics.endFill();



        // 2. Внешний 3D-обод капсулы



        var bMat:Matrix = new Matrix();



        bMat.createGradientBox(this.mW, this.mH, Math.PI / 2, 0, 0);



        this.mBg.graphics.beginGradientFill(



            GradientType.LINEAR,



            [0xD2D7E0, 0xA0A6B2, 0x6C6F75],



            [1.0, 1.0, 1.0],



            [0, 175, 255],



            bMat



        );



        this.mBg.graphics.drawRoundRect(0, 0, this.mW, this.mH, this.mH, this.mH);



        this.mBg.graphics.endFill();



        // 3. Верхний внутренний 1px чисто-белый блик (#FFFFFF)



        this.mBg.graphics.beginFill(0xFFFFFF, 1.0);



        this.mBg.graphics.drawRoundRect(1, 1, this.mW - 2, this.mH - 2, this.mH - 2, this.mH - 2);



        this.mBg.graphics.endFill();



        // 4. Выпуклая серебристо-жемчужная капсула



        var mat:Matrix = new Matrix();



        mat.createGradientBox(this.mW - 2, this.mH - 3, Math.PI / 2, 1, 2);



        var topCol:uint = 0xFFFFFF;



        var midCol:uint = hover ? 0xFCFCFC : 0xEEEEEE;



        var botCol:uint = hover ? 0xF0F0F0 : 0xDADADA;



        this.mBg.graphics.beginGradientFill(



            GradientType.LINEAR,



            [topCol, midCol, botCol],



            [1.0, 1.0, 1.0],



            [0, 140, 255],



            mat



        );



        this.mBg.graphics.drawRoundRect(1, 2, this.mW - 2, this.mH - 3, this.mH - 3, this.mH - 3);



        this.mBg.graphics.endFill();



    }



}



// =========================================================================



// SYNAPSE BALLOON STUDIO UI — REAL-TIME 3D PREVIEW & CUSTOMIZER



// =========================================================================



class StudioSectionTitle extends Sprite



{



    public function StudioSectionTitle(titleStr:String, w:Number)



    {



        super();



        var bg:Shape = new Shape();



        bg.graphics.beginFill(0xDFE8F2, 1.0);



        bg.graphics.drawRoundRect(0, 0, w, 22, 4, 4);



        bg.graphics.endFill();



        addChild(bg);



        var tf:TextField = SettingsUI.makeText(titleStr, 11, 0x19456B);



        tf.x = 8;



        tf.y = 3;



        addChild(tf);



    }



}



class StudioStepperRow extends Sprite



{



    private var mCurVal:Number;



    private var mMinVal:Number;



    private var mMaxVal:Number;



    private var mStepVal:Number;



    private var mUnitStr:String;



    private var mValTf:TextField;



    private var mOnChange:Function;



    public function StudioStepperRow(labelStr:String, minVal:Number, maxVal:Number, stepVal:Number, initialVal:Number, unitStr:String, onChange:Function)



    {



        super();



        this.mMinVal = minVal;



        this.mMaxVal = maxVal;



        this.mStepVal = stepVal;



        this.mCurVal = initialVal;



        this.mUnitStr = unitStr;



        this.mOnChange = onChange;



        var lbl:TextField = SettingsUI.makeText(labelStr, 11, 0x19456B);



        lbl.x = 8;



        lbl.y = 3;



        addChild(lbl);



        this.mValTf = SettingsUI.makeCenteredText(this.formatVal(this.mCurVal), 11, 0x0A4E9E, 64);



        this.mValTf.x = 206;



        this.mValTf.y = 3;



        addChild(this.mValTf);



        var selfRef:StudioStepperRow = this;



        var btnMinus:SimsPillButton = new SimsPillButton("-", 26, 22, "custom_action", "", null, false, 12);



        btnMinus.x = 176;



        btnMinus.y = 0;



        btnMinus.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            var nVal:Number = selfRef.mCurVal - selfRef.mStepVal;



            if(nVal < selfRef.mMinVal) nVal = selfRef.mMinVal;



            selfRef.mCurVal = Math.round(nVal * 100) / 100;



            selfRef.mValTf.text = selfRef.formatVal(selfRef.mCurVal);



            if(selfRef.mOnChange != null) selfRef.mOnChange(selfRef.mCurVal);



        });



        addChild(btnMinus);



        var btnPlus:SimsPillButton = new SimsPillButton("+", 26, 22, "custom_action", "", null, false, 12);



        btnPlus.x = 274;



        btnPlus.y = 0;



        btnPlus.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            var nVal:Number = selfRef.mCurVal + selfRef.mStepVal;



            if(nVal > selfRef.mMaxVal) nVal = selfRef.mMaxVal;



            selfRef.mCurVal = Math.round(nVal * 100) / 100;



            selfRef.mValTf.text = selfRef.formatVal(selfRef.mCurVal);



            if(selfRef.mOnChange != null) selfRef.mOnChange(selfRef.mCurVal);



        });



        addChild(btnPlus);



    }



    public function getValue():Number



    {



        return this.mCurVal;



    }



    public function setValue(v:Number):void



    {



        this.mCurVal = v;



        this.mValTf.text = this.formatVal(this.mCurVal);



    }



    private function formatVal(v:Number):String



    {



        if(this.mUnitStr == " (h)" || this.mUnitStr == " (x)")



        {



            var sign:String = (this.mUnitStr == " (x)" && v > 0) ? "+" : "";



            return sign + (v / 100).toFixed(2) + " м";



        }



        if(this.mUnitStr == " с/с")



        {



            if(v <= 0) return "Сразу";



            return String(v) + " с/с";



        }



        if(this.mUnitStr == "x")



        {



            return (v / 100).toFixed(1) + "x";



        }



        return String(v) + this.mUnitStr;



    }



}



class BalloonStudioUI extends Sprite



{



    public static const PANEL_W:Number = 340;



    public static const PANEL_H:Number = 570;



    private var mBoot:Boot;



    private var mSettings:SettingsUI;



    private var mSimId:String;



    private var mSimName:String;



    private var mTestText:String = "Привет! Это предпросмотр бабла над симом. Всё настраивается в реальном времени!";



    private var mBalloonType:String = "speech";



    private var mInitialStyleBackup:Object = {};



    private var mDragging:Boolean = false;



    private var mDragOffX:Number = 0;



    private var mDragOffY:Number = 0;



    private var mScrollView:MaxisScrollView;



    private var mTextInput:TextField;



    private var mBtnSpeech:SimsPillButton;



    private var mBtnThought:SimsPillButton;



    private var mThemeLightBtn:SimsPillButton;



    private var mThemeDarkBtn:SimsPillButton;



    private var mThemeWarmBtn:SimsPillButton;



    // Steppers and checkboxes



    private var mStScale:StudioStepperRow;



    private var mStWidth:StudioStepperRow;



    private var mStOffsetY:StudioStepperRow;



    private var mStOffsetX:StudioStepperRow;



    private var mStRadius:StudioStepperRow;



    private var mStPadX:StudioStepperRow;



    private var mStPadY:StudioStepperRow;



    private var mStFontSize:StudioStepperRow;



    private var mStLeading:StudioStepperRow;



    private var mCbShowName:SimsCheckbox;



    private var mStNameFont:StudioStepperRow;



    private var mStAlpha:StudioStepperRow;



    private var mCbCamScale:SimsCheckbox;



    private var mStMinScale:StudioStepperRow;



    private var mStSpeed:StudioStepperRow;



    private var mStDur:StudioStepperRow;



    public function BalloonStudioUI(bootInst:Boot, settingsInst:SettingsUI, simId:String, simName:String)



    {



        super();



        this.mBoot = bootInst;



        this.mSettings = settingsInst;



        this.mSimId = simId;



        this.mSimName = simName;



        try



        {



            var bs:Object = Boot.sBalloonStyle;



            if (bs != null)



            {



                for (var k:String in bs)



                {



                    this.mInitialStyleBackup[k] = bs[k];



                }



            }



            this.buildUI();



            Boot.sendServerLog("BalloonStudioUI initialized successfully");

        }

        catch (eBui:Error)

        {

            Boot.sendServerLog("BalloonStudioUI CRASH: " + eBui.message);

        }



    }



    private function buildUI():void



    {



        var selfRef:BalloonStudioUI = this;



        // Drop shadows



        var shadow1:Shape = new Shape();



        shadow1.graphics.beginFill(0x000000, 0.08);



        shadow1.graphics.drawRoundRect(-5, -2, PANEL_W + 10, PANEL_H + 10, 16, 16);



        shadow1.graphics.endFill();



        addChild(shadow1);



        var shadow2:Shape = new Shape();



        shadow2.graphics.beginFill(0x000000, 0.16);



        shadow2.graphics.drawRoundRect(-2, 0, PANEL_W + 4, PANEL_H + 5, 14, 14);



        shadow2.graphics.endFill();



        addChild(shadow2);



        // White body



        var bodyBg:Shape = new Shape();



        bodyBg.graphics.beginFill(0xFFFFFF, 1.0);



        bodyBg.graphics.drawRoundRect(0, 0, PANEL_W, PANEL_H, 12, 12);



        bodyBg.graphics.endFill();



        addChild(bodyBg);



        var outerBorder:Shape = new Shape();



        outerBorder.graphics.lineStyle(1.5, 0xBAC7D5, 1.0, true);



        outerBorder.graphics.drawRoundRect(0, 0, PANEL_W, PANEL_H, 12, 12);



        addChild(outerBorder);



        // Header (32px)



        var barH:Number = 32;



        var hdrTop:Shape = new Shape();



        hdrTop.graphics.beginFill(SettingsUI.COL_SEC_HEADER, 1.0);



        hdrTop.graphics.drawRoundRect(0, 0, PANEL_W, barH, 12, 12);



        hdrTop.graphics.endFill();



        addChild(hdrTop);



        var hdrFlatBot:Shape = new Shape();



        hdrFlatBot.graphics.beginFill(SettingsUI.COL_SEC_HEADER, 1.0);



        hdrFlatBot.graphics.drawRect(0, barH - 8, PANEL_W, 8);



        hdrFlatBot.graphics.endFill();



        addChild(hdrFlatBot);



        var hdrSep:Shape = new Shape();



        hdrSep.graphics.beginFill(0x8A9CAE, 1.0);



        hdrSep.graphics.drawRect(0, barH - 1, PANEL_W, 1);



        hdrSep.graphics.endFill();



        addChild(hdrSep);



        var titleTf:TextField = SettingsUI.makeText("КОНСТРУКТОР БАБЛОВ", 12, 0xFFFFFF);



        titleTf.x = 14;



        titleTf.y = 7;



        addChild(titleTf);



        // Header Drag Area



        var dragArea:Sprite = new Sprite();



        dragArea.graphics.beginFill(0x000000, 0.001);



        dragArea.graphics.drawRect(0, 0, PANEL_W - 34, barH);



        dragArea.graphics.endFill();



        dragArea.buttonMode = true;



        dragArea.addEventListener(MouseEvent.MOUSE_DOWN, this.onHeaderMouseDown);



        addChild(dragArea);



        // Circular Close Button [X]



        var closeBtn:Sprite = new Sprite();



        closeBtn.buttonMode = true;



        closeBtn.mouseChildren = false;



        closeBtn.x = PANEL_W - 27;



        closeBtn.y = 6;



        var closeBg:Shape = new Shape();



        var closeIcon:Shape = new Shape();



        closeBtn.addChild(closeBg);



        closeBtn.addChild(closeIcon);



        closeBg.graphics.beginFill(0x000000, 0.12);



        closeBg.graphics.drawCircle(10, 11, 10);



        closeBg.graphics.endFill();



        closeBg.graphics.beginFill(0x7F8D9D, 1.0);



        closeBg.graphics.drawCircle(10, 10, 10);



        closeBg.graphics.endFill();



        var cMat:Matrix = new Matrix();



        cMat.createGradientBox(18, 18, Math.PI / 2, 1, 1);



        closeBg.graphics.beginGradientFill(GradientType.LINEAR, [0xFFFFFF, 0xDFE6EE], [1.0, 1.0], [0, 255], cMat);



        closeBg.graphics.drawCircle(10, 10, 8.8);



        closeBg.graphics.endFill();



        closeIcon.graphics.lineStyle(2.0, 0x19456B, 1.0);



        closeIcon.graphics.moveTo(6.8, 6.8);



        closeIcon.graphics.lineTo(13.2, 13.2);



        closeIcon.graphics.moveTo(13.2, 6.8);



        closeIcon.graphics.lineTo(6.8, 13.2);



        closeBtn.addEventListener(MouseEvent.ROLL_OVER, function(e:MouseEvent):void {



            closeIcon.graphics.clear();



            closeIcon.graphics.lineStyle(2.0, SettingsUI.COL_HOVER_GREEN, 1.0);



            closeIcon.graphics.moveTo(6.8, 6.8);



            closeIcon.graphics.lineTo(13.2, 13.2);



            closeIcon.graphics.moveTo(13.2, 6.8);



            closeIcon.graphics.lineTo(6.8, 13.2);



        });



        closeBtn.addEventListener(MouseEvent.ROLL_OUT, function(e:MouseEvent):void {



            closeIcon.graphics.clear();



            closeIcon.graphics.lineStyle(2.0, 0x19456B, 1.0);



            closeIcon.graphics.moveTo(6.8, 6.8);



            closeIcon.graphics.lineTo(13.2, 13.2);



            closeIcon.graphics.moveTo(13.2, 6.8);



            closeIcon.graphics.lineTo(6.8, 13.2);



        });



        closeBtn.addEventListener(MouseEvent.CLICK, this.onCancelClick);



        addChild(closeBtn);



        // Click on panel releases text input focus so WASD camera works



        addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            if (e.target != selfRef.mTextInput)



            {



                try {



                    var cm:Object = getDefinitionByName("olympus.io.CommunicationManager");



                    cm.CallGameService("SetTextFieldInput", false);



                } catch(eFo:Error) {}



            }



        });



        // Scrollview (viewport height = 486)



        var scrollH:Number = PANEL_H - barH - 48;



        this.mScrollView = new MaxisScrollView(PANEL_W - 14, scrollH);



        this.mScrollView.x = 8;



        this.mScrollView.y = barH + 4;



        addChild(this.mScrollView);



        var contentSp:Sprite = this.mScrollView.getContent();



        var curY:Number = 4;



        var rowW:Number = 306;



        // --- SECTION 1: ТЕСТ И КАМЕРА ---



        var sec1:StudioSectionTitle = new StudioSectionTitle("1. ТЕСТ ТЕКСТА И КАМЕРА", rowW);



        sec1.y = curY;



        contentSp.addChild(sec1);



        curY += 26;



        // Text input field



        var inBg:Shape = new Shape();



        inBg.graphics.lineStyle(1, 0xCBD6E2, 1.0, true);



        inBg.graphics.beginFill(0xF8FAFD, 1.0);



        inBg.graphics.drawRoundRect(4, curY, rowW - 4, 46, 4, 4);



        inBg.graphics.endFill();



        contentSp.addChild(inBg);



        this.mTextInput = new TextField();



        this.mTextInput.type = "input";



        this.mTextInput.embedFonts = true;



        this.mTextInput.selectable = true;



        this.mTextInput.mouseEnabled = true;



        this.mTextInput.multiline = true;



        this.mTextInput.wordWrap = true;



        this.mTextInput.maxChars = 240;



        this.mTextInput.text = this.mTestText;



        this.mTextInput.x = 8;



        this.mTextInput.y = curY + 2;



        this.mTextInput.width = rowW - 12;



        this.mTextInput.height = 42;



        var tFmt:TextFormat = new TextFormat("$TextFont", 11, SettingsUI.COL_LABEL_DARK, false);



        this.mTextInput.defaultTextFormat = tFmt;



        this.mTextInput.setTextFormat(tFmt);



        this.mTextInput.addEventListener(FocusEvent.FOCUS_IN, function(e:FocusEvent):void {



            try {



                var cmFi:Object = getDefinitionByName("olympus.io.CommunicationManager");



                cmFi.CallGameService("SetTextFieldInput", true);



            } catch(eFi:Error) {}



        });



        this.mTextInput.addEventListener(Event.CHANGE, function(e:Event):void {



            selfRef.mTestText = selfRef.mTextInput.text;



            selfRef.updatePreview();



        });



        contentSp.addChild(this.mTextInput);



        curY += 50;



        // Presets row (3 buttons)



        var pBtn1:SimsPillButton = new SimsPillButton("Короткий", 96, 22, "custom_action", "", null, false, 10);



        pBtn1.x = 4;



        pBtn1.y = curY;



        pBtn1.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.mTextInput.text = "Привет, как дела?";



            selfRef.mTestText = selfRef.mTextInput.text;



            selfRef.updatePreview();



        });



        contentSp.addChild(pBtn1);



        var pBtn2:SimsPillButton = new SimsPillButton("Средний", 98, 22, "custom_action", "", null, false, 10);



        pBtn2.x = 104;



        pBtn2.y = curY;



        pBtn2.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.mTextInput.text = "Дэзи, плита вообще не включается, и телевизор молчит.";



            selfRef.mTestText = selfRef.mTextInput.text;



            selfRef.updatePreview();



        });



        contentSp.addChild(pBtn2);



        var pBtn3:SimsPillButton = new SimsPillButton("Длинный", 98, 22, "custom_action", "", null, false, 10);



        pBtn3.x = 206;



        pBtn3.y = curY;



        pBtn3.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.mTextInput.text = "Я сегодня весь день думал о том, как странно устроена жизнь в нашем районе. Техника постоянно ломается!";



            selfRef.mTestText = selfRef.mTextInput.text;



            selfRef.updatePreview();



        });



        contentSp.addChild(pBtn3);



        curY += 28;



        // Type row (Speech vs Thought)



        this.mBtnSpeech = new SimsPillButton("Речь (хвостик)", 148, 24, "custom_action", "", null, false, 11);



        this.mBtnSpeech.x = 4;



        this.mBtnSpeech.y = curY;



        this.mBtnSpeech.setSelected(this.mBalloonType == "speech");



        this.mBtnSpeech.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.mBalloonType = "speech";



            selfRef.mBtnSpeech.setSelected(true);



            selfRef.mBtnThought.setSelected(false);



            selfRef.updatePreview();



        });



        contentSp.addChild(this.mBtnSpeech);



        this.mBtnThought = new SimsPillButton("Мысль (облако)", 148, 24, "custom_action", "", null, false, 11);



        this.mBtnThought.x = 156;



        this.mBtnThought.y = curY;



        this.mBtnThought.setSelected(this.mBalloonType == "thought");



        this.mBtnThought.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            selfRef.mBalloonType = "thought";



            selfRef.mBtnSpeech.setSelected(false);



            selfRef.mBtnThought.setSelected(true);



            selfRef.updatePreview();



        });



        contentSp.addChild(this.mBtnThought);



        curY += 30;



        // Camera focus & Replay Animation buttons



        var btnCam:SimsPillButton = new SimsPillButton("Камера к симу", 148, 24, "custom_action", "", null, false, 11);



        btnCam.x = 4;



        btnCam.y = curY;



        btnCam.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            if (ExternalInterface.available)



            {



                ExternalInterface.call("CallGameService", "PostServerCommand", {



                    "command": "synapse.balloon_studio_focus",



                    "commandArgs": [selfRef.mSimId]



                }, false);



            }



        });



        contentSp.addChild(btnCam);



        var btnReplay:SimsPillButton = new SimsPillButton("Повторить анимацию", 148, 24, "custom_action", "", null, false, 11);



        btnReplay.x = 156;



        btnReplay.y = curY;



        btnReplay.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            Boot.replayStudioPreviewAnimation();



        });



        contentSp.addChild(btnReplay);



        curY += 34;



        // --- SECTION 2: РАЗМЕРЫ И ПОЛОЖЕНИЕ ---



        var sec2:StudioSectionTitle = new StudioSectionTitle("2. РАЗМЕРЫ И ГЕОМЕТРИЯ", rowW);



        sec2.y = curY;



        contentSp.addChild(sec2);



        curY += 26;



        var bs:Object = Boot.sBalloonStyle;



        this.mStScale = new StudioStepperRow("Общий масштаб:", 60, 180, 5, Number(bs.scale_pct || 100), "%", function(v:Number):void {



            Boot.sBalloonStyle.scale_pct = v;



            selfRef.updatePreview();



        });



        this.mStScale.y = curY;



        contentSp.addChild(this.mStScale);



        curY += 26;



        this.mStWidth = new StudioStepperRow("Макс. ширина:", 160, 420, 10, Number(bs.max_width || 260), " px", function(v:Number):void {



            Boot.sBalloonStyle.max_width = v;



            selfRef.updatePreview();



        });



        this.mStWidth.y = curY;



        contentSp.addChild(this.mStWidth);



        curY += 26;



        this.mStOffsetY = new StudioStepperRow("Высота над головой:", 10, 75, 2, Number(bs.offset_y || 32), " (h)", function(v:Number):void {



            Boot.sBalloonStyle.offset_y = v;



            selfRef.updatePreview();



        });



        this.mStOffsetY.y = curY;



        contentSp.addChild(this.mStOffsetY);



        curY += 26;



        this.mStOffsetX = new StudioStepperRow("Смещение влево/вправо:", -40, 40, 2, Number(bs.offset_x || 0), " (x)", function(v:Number):void {



            Boot.sBalloonStyle.offset_x = v;



            selfRef.updatePreview();



        });



        this.mStOffsetX.y = curY;



        contentSp.addChild(this.mStOffsetX);



        curY += 26;



        this.mStRadius = new StudioStepperRow("Скругление углов:", 4, 26, 1, Number(bs.radius || 15), " px", function(v:Number):void {



            Boot.sBalloonStyle.radius = v;



            selfRef.updatePreview();



        });



        this.mStRadius.y = curY;



        contentSp.addChild(this.mStRadius);



        curY += 26;



        this.mStPadX = new StudioStepperRow("Внутренние поля X:", 8, 26, 1, Number(bs.pad_x || 16), " px", function(v:Number):void {



            Boot.sBalloonStyle.pad_x = v;



            selfRef.updatePreview();



        });



        this.mStPadX.y = curY;



        contentSp.addChild(this.mStPadX);



        curY += 26;



        this.mStPadY = new StudioStepperRow("Внутренние поля Y:", 6, 22, 1, Number(bs.pad_y || 13), " px", function(v:Number):void {



            Boot.sBalloonStyle.pad_y = v;



            selfRef.updatePreview();



        });



        this.mStPadY.y = curY;



        contentSp.addChild(this.mStPadY);



        curY += 32;



        // --- SECTION 3: ШРИФТЫ, ТЕМА И КАМЕРА ---



        var sec3:StudioSectionTitle = new StudioSectionTitle("3. ШРИФТЫ, ТЕМА И КАМЕРА", rowW);



        sec3.y = curY;



        contentSp.addChild(sec3);



        curY += 26;



        this.mStFontSize = new StudioStepperRow("Размер шрифта:", 11, 22, 1, Number(bs.font_size || 15), " px", function(v:Number):void {



            Boot.sBalloonStyle.font_size = v;



            selfRef.updatePreview();



        });



        this.mStFontSize.y = curY;



        contentSp.addChild(this.mStFontSize);



        curY += 26;



        this.mStLeading = new StudioStepperRow("Межстрочный интервал:", 1, 8, 1, Number(bs.leading || 4), " px", function(v:Number):void {



            Boot.sBalloonStyle.leading = v;



            selfRef.updatePreview();



        });



        this.mStLeading.y = curY;



        contentSp.addChild(this.mStLeading);



        curY += 28;



        // Checkbox: Show Name



        var cbNameRow:Sprite = new Sprite();



        cbNameRow.y = curY;



        this.mCbShowName = new SimsCheckbox("studio_show_name", bs.show_name !== false, function(k:String, st:Boolean):void {



            Boot.sBalloonStyle.show_name = st;



            selfRef.updatePreview();



        });



        this.mCbShowName.x = 8;



        this.mCbShowName.y = 2;



        cbNameRow.addChild(this.mCbShowName);



        var cbNameLbl:TextField = SettingsUI.makeText("Показывать имя сима", 11, 0x19456B);



        cbNameLbl.x = 34;



        cbNameLbl.y = 2;



        cbNameRow.addChild(cbNameLbl);



        contentSp.addChild(cbNameRow);



        curY += 28;



        this.mStNameFont = new StudioStepperRow("Шрифт имени:", 9, 16, 1, Number(bs.name_font_size || 11), " px", function(v:Number):void {



            Boot.sBalloonStyle.name_font_size = v;



            selfRef.updatePreview();



        });



        this.mStNameFont.y = curY;



        contentSp.addChild(this.mStNameFont);



        curY += 28;



        // Theme buttons row



        var thmLbl:TextField = SettingsUI.makeText("Тема оформления:", 11, 0x19456B);



        thmLbl.x = 8;



        thmLbl.y = curY;



        contentSp.addChild(thmLbl);



        curY += 20;



        var curThm:String = String(bs.theme || "light");



        this.mThemeLightBtn = new SimsPillButton("Светлая", 96, 22, "custom_action", "", null, false, 10);



        this.mThemeLightBtn.x = 4;



        this.mThemeLightBtn.y = curY;



        this.mThemeLightBtn.setSelected(curThm == "light");



        this.mThemeLightBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            Boot.sBalloonStyle.theme = "light";



            selfRef.updateThemeButtons();



            selfRef.updatePreview();



        });



        contentSp.addChild(this.mThemeLightBtn);



        this.mThemeDarkBtn = new SimsPillButton("Тёмная", 98, 22, "custom_action", "", null, false, 10);



        this.mThemeDarkBtn.x = 104;



        this.mThemeDarkBtn.y = curY;



        this.mThemeDarkBtn.setSelected(curThm == "dark");



        this.mThemeDarkBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            Boot.sBalloonStyle.theme = "dark";



            selfRef.updateThemeButtons();



            selfRef.updatePreview();



        });



        contentSp.addChild(this.mThemeDarkBtn);



        this.mThemeWarmBtn = new SimsPillButton("Кремовая", 98, 22, "custom_action", "", null, false, 10);



        this.mThemeWarmBtn.x = 206;



        this.mThemeWarmBtn.y = curY;



        this.mThemeWarmBtn.setSelected(curThm == "warm");



        this.mThemeWarmBtn.addEventListener(MouseEvent.CLICK, function(e:MouseEvent):void {



            Boot.sBalloonStyle.theme = "warm";



            selfRef.updateThemeButtons();



            selfRef.updatePreview();



        });



        contentSp.addChild(this.mThemeWarmBtn);



        curY += 28;



        this.mStAlpha = new StudioStepperRow("Прозрачность фона:", 60, 100, 5, Number(bs.bg_alpha_pct || 98), "%", function(v:Number):void {



            Boot.sBalloonStyle.bg_alpha_pct = v;



            selfRef.updatePreview();



        });



        this.mStAlpha.y = curY;



        contentSp.addChild(this.mStAlpha);



        curY += 28;



        // Checkbox: Camera Scale



        var cbCamRow:Sprite = new Sprite();



        cbCamRow.y = curY;



        this.mCbCamScale = new SimsCheckbox("studio_cam_scale", bs.camera_scale !== false, function(k:String, st:Boolean):void {



            Boot.sBalloonStyle.camera_scale = st;



            selfRef.updatePreview();



        });



        this.mCbCamScale.x = 8;



        this.mCbCamScale.y = 2;



        cbCamRow.addChild(this.mCbCamScale);



        var cbCamLbl:TextField = SettingsUI.makeText("Уменьшать при отдалении камеры", 11, 0x19456B);



        cbCamLbl.x = 34;



        cbCamLbl.y = 2;



        cbCamRow.addChild(cbCamLbl);



        contentSp.addChild(cbCamRow);



        curY += 28;



        this.mStMinScale = new StudioStepperRow("Мин. размер вдалеке:", 20, 100, 5, Number(bs.min_scale_pct || 35), "%", function(v:Number):void {



            Boot.sBalloonStyle.min_scale_pct = v;



            selfRef.updatePreview();



        });



        this.mStMinScale.y = curY;



        contentSp.addChild(this.mStMinScale);



        curY += 26;



        this.mStSpeed = new StudioStepperRow("Скорость печати:", 0, 90, 5, Number(bs.type_speed != null ? bs.type_speed : 35), " с/с", function(v:Number):void {



            Boot.sBalloonStyle.type_speed = v;



        });



        this.mStSpeed.y = curY;



        contentSp.addChild(this.mStSpeed);



        curY += 26;



        this.mStDur = new StudioStepperRow("Длительность висения:", 50, 250, 10, Number(bs.duration_pct || 100), "%", function(v:Number):void {



            Boot.sBalloonStyle.duration_pct = v;



        });



        this.mStDur.y = curY;



        contentSp.addChild(this.mStDur);



        curY += 34;



        this.mScrollView.updateLayout(curY);



        // Footer Bar (46px at bottom)



        var footY:Number = PANEL_H - 46;



        var footBg:Shape = new Shape();



        var footMat:Matrix = new Matrix();



        footMat.createGradientBox(PANEL_W, 46, Math.PI / 2, 0, footY);



        footBg.graphics.beginGradientFill(



            GradientType.LINEAR,



            [SettingsUI.COL_FOOTER_TOP, SettingsUI.COL_FOOTER_BOT],



            [1.0, 1.0],



            [0, 255],



            footMat



        );



        footBg.graphics.drawRoundRect(0, footY, PANEL_W, 46, 12, 12);



        footBg.graphics.endFill();



        addChild(footBg);



        var footTopFlat:Shape = new Shape();



        footTopFlat.graphics.beginFill(SettingsUI.COL_FOOTER_TOP, 1.0);



        footTopFlat.graphics.drawRect(0, footY, PANEL_W, 10);



        footTopFlat.graphics.endFill();



        addChild(footTopFlat);



        var footSep:Shape = new Shape();



        footSep.graphics.beginFill(0x9FA9BD, 1.0);



        footSep.graphics.drawRect(0, footY, PANEL_W, 1);



        footSep.graphics.endFill();



        addChild(footSep);



        // Footer Buttons



        var btnSave:SimsPillButton = new SimsPillButton("Сохранить", 96, 26, "custom_action", "", null, false, 11);



        btnSave.x = 12;



        btnSave.y = footY + 10;



        btnSave.addEventListener(MouseEvent.CLICK, this.onSaveClick);



        addChild(btnSave);



        var btnReset:SimsPillButton = new SimsPillButton("По умолч.", 96, 26, "custom_action", "", null, false, 11);



        btnReset.x = 114;



        btnReset.y = footY + 10;



        btnReset.addEventListener(MouseEvent.CLICK, this.onResetClick);



        addChild(btnReset);



        var btnCancel:SimsPillButton = new SimsPillButton("Отмена", 84, 26, "custom_action", "", null, false, 11);



        btnCancel.x = 244;



        btnCancel.y = footY + 10;



        btnCancel.addEventListener(MouseEvent.CLICK, this.onCancelClick);



        addChild(btnCancel);



    }



    private function updateThemeButtons():void



    {



        var cur:String = String(Boot.sBalloonStyle.theme || "light");



        if(this.mThemeLightBtn) this.mThemeLightBtn.setSelected(cur == "light");



        if(this.mThemeDarkBtn) this.mThemeDarkBtn.setSelected(cur == "dark");



        if(this.mThemeWarmBtn) this.mThemeWarmBtn.setSelected(cur == "warm");



    }



    private function updatePreview():void



    {



        Boot.updateStudioPreview(this.mTestText, this.mBalloonType);



    }



    private function onHeaderMouseDown(e:MouseEvent):void



    {



        if (stage)



        {



            this.mDragging = true;



            this.mDragOffX = stage.mouseX - this.x;



            this.mDragOffY = stage.mouseY - this.y;



            stage.addEventListener(MouseEvent.MOUSE_MOVE, this.onStageMouseMove);



            stage.addEventListener(MouseEvent.MOUSE_UP, this.onStageMouseUp);



        }



    }



    private function onStageMouseMove(e:MouseEvent):void



    {



        if (this.mDragging && stage)



        {



            this.x = Math.max(0, Math.min(stage.stageWidth - PANEL_W, stage.mouseX - this.mDragOffX));



            this.y = Math.max(0, Math.min(stage.stageHeight - PANEL_H, stage.mouseY - this.mDragOffY));



        }



    }



    private function onStageMouseUp(e:MouseEvent):void



    {



        this.mDragging = false;



        if (stage)



        {



            stage.removeEventListener(MouseEvent.MOUSE_MOVE, this.onStageMouseMove);



            stage.removeEventListener(MouseEvent.MOUSE_UP, this.onStageMouseUp);



        }



    }



    private function onSaveClick(e:MouseEvent):void



    {



        // Pack style string



        var bs:Object = Boot.sBalloonStyle;



        var parts:Array = [];



        var keys:Array = [



            "scale_pct", "max_width", "font_size", "leading", "show_name",



            "name_font_size", "pad_x", "pad_y", "radius", "offset_y",



            "offset_x", "camera_scale", "min_scale_pct", "bg_alpha_pct",



            "theme", "type_speed", "duration_pct"



        ];



        for (var i:int = 0; i < keys.length; i++)



        {



            var k:String = String(keys[i]);



            var v:* = bs[k];



            if (v is Boolean)



            {



                parts.push(k + ":" + (v ? "1" : "0"));



            }



            else



            {



                parts.push(k + ":" + String(v));



            }



        }



        var packed:String = parts.join(";");



        if (ExternalInterface.available)



        {



            ExternalInterface.call("CallGameService", "PostServerCommand", {



                "command": "synapse.set_balloon_style",



                "commandArgs": [packed]



            }, false);



        }



        if (this.mSettings != null)



        {



            this.mSettings.closeBalloonStudio(true);



        }



    }



    private function onResetClick(e:MouseEvent):void



    {



        Boot.sBalloonStyle = {



            scale_pct: 100,



            max_width: 260,



            font_size: 15,



            leading: 4,



            show_name: true,



            name_font_size: 11,



            pad_x: 16,



            pad_y: 13,



            radius: 15,



            offset_y: 32,



            offset_x: 0,



            camera_scale: true,



            min_scale_pct: 35,



            bg_alpha_pct: 98,



            theme: "light",



            type_speed: 35,



            duration_pct: 100



        };



        var bs:Object = Boot.sBalloonStyle;



        if (this.mStScale) this.mStScale.setValue(100);



        if (this.mStWidth) this.mStWidth.setValue(260);



        if (this.mStOffsetY) this.mStOffsetY.setValue(32);



        if (this.mStOffsetX) this.mStOffsetX.setValue(0);



        if (this.mStRadius) this.mStRadius.setValue(15);



        if (this.mStPadX) this.mStPadX.setValue(16);



        if (this.mStPadY) this.mStPadY.setValue(13);



        if (this.mStFontSize) this.mStFontSize.setValue(15);



        if (this.mStLeading) this.mStLeading.setValue(4);



        if (this.mCbShowName) this.mCbShowName.setState(true);



        if (this.mStNameFont) this.mStNameFont.setValue(11);



        if (this.mStAlpha) this.mStAlpha.setValue(98);



        if (this.mCbCamScale) this.mCbCamScale.setState(true);



        if (this.mStMinScale) this.mStMinScale.setValue(35);



        if (this.mStSpeed) this.mStSpeed.setValue(35);



        if (this.mStDur) this.mStDur.setValue(100);



        this.updateThemeButtons();



        this.updatePreview();



    }



    private function onCancelClick(e:MouseEvent):void



    {



        // Restore backup



        for (var k:String in this.mInitialStyleBackup)



        {



            Boot.sBalloonStyle[k] = this.mInitialStyleBackup[k];



        }



        if (this.mSettings != null)



        {



            this.mSettings.closeBalloonStudio(false);



        }



    }



}



