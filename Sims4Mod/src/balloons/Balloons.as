package s4ai.boot
{
   import flash.display.MovieClip;
   import flash.display.Shape;
   import flash.display.Sprite;
   import flash.events.Event;
   import flash.external.ExternalInterface;
   import flash.filters.DropShadowFilter;
   import flash.geom.Matrix;
   import flash.display.GradientType;
   import flash.text.TextField;
   import flash.text.TextFieldAutoSize;
   import flash.text.TextFormat;
   import flash.utils.Dictionary;
   import flash.utils.getDefinitionByName;
   import flash.utils.getTimer;
   import flash.utils.setTimeout;
   
   [SWF(width="1024", height="768", frameRate="30")]
   public class Boot extends Sprite
   {
      private static const SLOT:String = "FacebookDisplay";
      private static const CMD_SHOW:String = "ui.synapse_balloon";
      private static const CMD_CLEAR:String = "ui.synapse_balloon_clear";
      private static const SERVER_READY:String = "synapse.ui_ready";
      
      public var widget:Object;
      private var balloonLayer:Sprite = new Sprite();
      private var activeBalloons:Dictionary = new Dictionary();
      private var isStarted:Boolean = false;
      
      public function Boot()
      {
         super();
         mouseEnabled = false;
         mouseChildren = false;
         
         this.balloonLayer.mouseEnabled = false;
         this.balloonLayer.mouseChildren = false;
         
         try
         {
            var wb:Class = getDefinitionByName("olympus.core.widget.WidgetBase") as Class;
            this.widget = new wb();
            this.widget.mcPositionHelper = new MovieClip();
         }
         catch(e:Error) {}
         
         try
         {
            var dbg:Object = getDefinitionByName("olympus.io.DebugCommands");
            dbg.Register(CMD_SHOW, this.onShowCommand, "Show Synapse AI Balloon", "simId name text duration");
            dbg.Register(CMD_CLEAR, this.onClearCommand, "Clear Synapse AI Balloons", "");
         }
         catch(e2:Error) {}
         
         addEventListener(Event.ADDED_TO_STAGE, this.onAdded, false, 0, true);
      }
      
      private function onAdded(e:Event):void
      {
         removeEventListener(Event.ADDED_TO_STAGE, this.onAdded);
         if(this.isStarted)
         {
            return;
         }
         this.isStarted = true;
         
         // Attach balloonLayer directly to the root Stage so it is never hidden or clipped
         if(stage)
         {
            stage.addChild(this.balloonLayer);
         }
         
         try
         {
            getDefinitionByName("olympus.io.CommunicationManager").AddMessageListenerByName("Show" + SLOT, this.onReshow, "SynapseBalloons");
         }
         catch(err:Error) {}
         
         // Safe delay to let C++ UI engine finish showing slot before releasing modality
         setTimeout(this.releaseModality, 1500);
         
         // Notify Python that the Flash UI is alive and ready
         try
         {
            ExternalInterface.call("CallGameService", "PostServerCommand", {
               "command": SERVER_READY,
               "commandArgs": []
            }, false);
         }
         catch(e3:Error) {}
         
         addEventListener(Event.ENTER_FRAME, this.onEnterFrame);
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
      
      private function onReshow(data:Object):void
      {
         setTimeout(this.releaseModality, 500);
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
         var simName:String = args.length > 1 ? this.decodeSafe(String(args[1])) : "";
         var text:String = args.length > 2 ? this.decodeSafe(String(args[2])) : "Привет!";
         var duration:Number = args.length > 3 ? Number(args[3]) : 6.0;
         if(isNaN(duration) || duration <= 0)
         {
            duration = 6.0;
         }
         
         this.createBalloon(simId, simName, text, duration);
      }
      
      private function createBalloon(simId:String, simName:String, text:String, durationSec:Number):void
      {
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
         
         var maxTextWidth:Number = 280;
         var padX:Number = 16;
         var padY:Number = 12;
         var radius:Number = 16;
         
         var tf:TextField = new TextField();
         tf.multiline = true;
         tf.wordWrap = true;
         tf.autoSize = TextFieldAutoSize.LEFT;
         tf.width = maxTextWidth;
         tf.selectable = false;
         
         var fmt:TextFormat = new TextFormat();
         fmt.font = "$TextFont";
         fmt.size = 15;
         fmt.color = 0x1E1E24;
         fmt.leading = 4;
         tf.defaultTextFormat = fmt;
         tf.text = text;
         
         if(tf.textWidth + 8 < maxTextWidth)
         {
            tf.width = tf.textWidth + 8;
         }
         
         var actualTextW:Number = tf.width;
         var actualTextH:Number = tf.height;
         
         var hasName:Boolean = simName != null && simName.length > 0 && simName != "null";
         var nameSprite:Sprite = new Sprite();
         var nameH:Number = 0;
         var nameW:Number = 0;
         
         if(hasName)
         {
            var ntf:TextField = new TextField();
            ntf.autoSize = TextFieldAutoSize.LEFT;
            ntf.selectable = false;
            
            var nfmt:TextFormat = new TextFormat();
            nfmt.font = "$BoldHeadlineFont";
            nfmt.size = 11;
            nfmt.color = 0xFFFFFF;
            nfmt.bold = true;
            ntf.defaultTextFormat = nfmt;
            ntf.text = simName;
            
            nameW = ntf.textWidth + 14;
            nameH = ntf.textHeight + 4;
            
            var nMat:Matrix = new Matrix();
            nMat.createGradientBox(nameW, nameH, Math.PI / 2, 0, 0);
            nameSprite.graphics.beginGradientFill(GradientType.LINEAR, [0x7A5CFA, 0x5D3EBC], [1, 1], [0, 255], nMat);
            nameSprite.graphics.drawRoundRect(0, 0, nameW, nameH, 8, 8);
            nameSprite.graphics.endFill();
            
            ntf.x = 7;
            ntf.y = 1;
            nameSprite.addChild(ntf);
         }
         
         var contentW:Number = Math.max(actualTextW, nameW);
         var boxW:Number = contentW + padX * 2;
         var boxH:Number = actualTextH + padY * 2 + (hasName ? nameH + 6 : 0);
         
         var left:Number = -boxW / 2;
         var top:Number = -boxH;
         
         var bg:Shape = new Shape();
         var bgMat:Matrix = new Matrix();
         bgMat.createGradientBox(boxW, boxH, Math.PI / 2, left, top);
         
         bg.graphics.lineStyle(1.8, 0xDADEE5, 0.95, true);
         bg.graphics.beginGradientFill(GradientType.LINEAR, [0xFFFFFF, 0xF4F6F9], [0.97, 0.97], [0, 255], bgMat);
         bg.graphics.drawRoundRect(left, top, boxW, boxH, radius, radius);
         bg.graphics.endFill();
         
         var tail:Shape = new Shape();
         tail.graphics.lineStyle(1.8, 0xDADEE5, 0.95, true);
         tail.graphics.beginFill(0xF4F6F9, 0.97);
         tail.graphics.moveTo(-9, top + boxH);
         tail.graphics.lineTo(0, 10);
         tail.graphics.lineTo(9, top + boxH);
         tail.graphics.endFill();
         
         body.addChild(bg);
         body.addChild(tail);
         
         var curY:Number = top + padY;
         if(hasName)
         {
            nameSprite.x = left + padX;
            nameSprite.y = curY;
            body.addChild(nameSprite);
            curY += nameH + 6;
         }
         
         tf.x = left + padX;
         tf.y = curY;
         body.addChild(tf);
         
         body.filters = [new DropShadowFilter(5, 90, 0x000000, 0.28, 10, 10, 1, 3)];
         
         body.scaleX = 0.2;
         body.scaleY = 0.2;
         body.alpha = 0;
         
         // Ensure balloonLayer is attached to stage
         if(!this.balloonLayer.stage && stage)
         {
            stage.addChild(this.balloonLayer);
         }
         this.balloonLayer.addChild(balloon);
         
         // Safety guard: ensure balloon is on stage to prevent C++ NULL dereference
         if(!balloon.stage)
         {
            return;
         }
         
         // Call C++ Game Service to bind to head bone
         ExternalInterface.call("CallGameService", "BindDisplayObject", {
            "displayObject": balloon,
            "objectId": simId,
            "attachPoint": "b__Head__",
            "worldOffset": {
               "x": 0,
               "y": 0.35,
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
            "isScaledByCamera": false,
            "minScale": 0.1,
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
            "startTime": getTimer(),
            "duration": durationSec * 1000,
            "state": "opening",
            "stateTime": getTimer()
         };
         
         this.activeBalloons[simId] = balloonData;
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
            
            if(b.state == "opening")
            {
               var openElapsed:Number = now - b.stateTime;
               var t:Number = Math.min(1.0, openElapsed / 220.0);
               var c1:Number = 1.70158;
               var c3:Number = c1 + 1;
               var s:Number = 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
               body.scaleX = Math.max(0, s);
               body.scaleY = Math.max(0, s);
               body.alpha = Math.min(1.0, t * 1.5);
               
               if(t >= 1.0)
               {
                  body.scaleX = 1.0;
                  body.scaleY = 1.0;
                  body.alpha = 1.0;
                  b.state = "holding";
                  b.stateTime = now;
               }
            }
            else if(b.state == "holding")
            {
               var holdElapsed:Number = now - b.stateTime;
               var breath:Number = 1.0 + 0.008 * Math.sin(holdElapsed * 0.003);
               body.scaleX = breath;
               body.scaleY = breath;
               
               if(elapsed >= b.duration)
               {
                  b.state = "closing";
                  b.stateTime = now;
               }
            }
            else if(b.state == "closing")
            {
               var closeElapsed:Number = now - b.stateTime;
               var ct:Number = Math.min(1.0, closeElapsed / 250.0);
               body.scaleX = 1.0 - ct * 0.3;
               body.scaleY = 1.0 - ct * 0.3;
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
         catch(e:Error) {}
         
         delete this.activeBalloons[b.simId];
      }
   }
}
