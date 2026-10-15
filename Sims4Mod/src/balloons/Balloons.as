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
            dbg.Register(CMD_SHOW, this.onShowCommand, "Show Synapse AI Balloon", "simId [type] name text duration");
            dbg.Register(CMD_CLEAR, this.onClearCommand, "Clear Synapse AI Balloons", "");
         }
         catch(e2:Error) {}
         
         // Immediately clear any modal state in constructor
         this.releaseModality();
         
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
         
         // Attach balloonLayer directly to root Stage
         if(stage)
         {
            stage.addChild(this.balloonLayer);
         }
         
         try
         {
            getDefinitionByName("olympus.io.CommunicationManager").AddMessageListenerByName("Show" + SLOT, this.onReshow, "SynapseBalloons");
         }
         catch(err:Error) {}
         
         // Release modality instantly and backup at 250ms
         this.releaseModality();
         setTimeout(this.releaseModality, 250);
         
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
         this.releaseModality();
         setTimeout(this.releaseModality, 200);
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
         
         this.createBalloon(simId, balloonType, simName, text, duration, colorTop, colorBot);
      }
      
      private function createBalloon(simId:String, balloonType:String, simName:String, text:String, durationSec:Number, colorTop:uint = 0, colorBot:uint = 0):void
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
         
         var isThought:Boolean = (balloonType == "thought");
         var maxTextWidth:Number = 290;
         var padX:Number = 18;
         var padY:Number = 14;
         var radius:Number = isThought ? 20 : 16;
         
         // Text field with Scaleform embedded font
         var tf:TextField = new TextField();
         tf.multiline = true;
         tf.wordWrap = true;
         tf.autoSize = TextFieldAutoSize.LEFT;
         tf.selectable = false;
         tf.mouseEnabled = false;
         tf.embedFonts = true;
         
         var fmt:TextFormat = new TextFormat("$TextFont", 15, 0x1E1E24);
         fmt.leading = 4;
         tf.defaultTextFormat = fmt;
         tf.width = maxTextWidth;
         tf.text = "";
         
         var hasName:Boolean = simName != null && simName.length > 0 && simName != "null";
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
            
            var nfmt:TextFormat = new TextFormat("$BoldHeadlineFont", 11, 0xFFFFFF, true);
            ntf.defaultTextFormat = nfmt;
            ntf.text = simName;
            
            var pillPadX:Number = 8;
            var pillPadY:Number = 3;
            nameH = Math.round(ntf.textHeight + pillPadY * 2 + 2);
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
         var initialBoxH:Number = 22 + padY * 2 + (hasName ? nameH + 8 : 0);
         
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
         
         // Ensure balloonLayer is attached to stage
         if(!this.balloonLayer.stage && stage)
         {
            stage.addChild(this.balloonLayer);
         }
         this.balloonLayer.addChild(balloon);
         
         // Safety guard: ensure balloon is on stage
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
               "y": 0.32,
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
            "isScaledByCamera": true,
            "minScale": 0.55,
            "maxVisibleScale": 1.15,
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
            "stateTime": getTimer()
         };
         
         this.activeBalloons[simId] = balloonData;
         this.redrawBalloon(balloonData);
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
         
         bg.graphics.clear();
         
         var bgMat:Matrix = new Matrix();
         bgMat.createGradientBox(boxW, boxH, Math.PI / 2, left, top);
         
         if(isThought)
         {
            bg.graphics.lineStyle(1.8, 0xD4D9E2, 0.95, true);
            bg.graphics.beginGradientFill(GradientType.LINEAR, [0xFFFFFF, 0xF4F6F9], [0.98, 0.98], [0, 255], bgMat);
            bg.graphics.drawRoundRect(left, top, boxW, boxH, radius, radius);
            bg.graphics.endFill();
            
            var tail:Shape = b.tail as Shape;
            if(tail != null)
            {
               tail.graphics.clear();
               tail.graphics.lineStyle(1.6, 0xD4D9E2, 0.95, true);
               tail.graphics.beginFill(0xFFFFFF, 0.98);
               tail.graphics.drawCircle(-6, top + boxH + 9, 5.0);
               tail.graphics.drawCircle(-3, top + boxH + 19, 3.5);
               tail.graphics.drawCircle(0, top + boxH + 27, 2.0);
               tail.graphics.endFill();
            }
         }
         else
         {
            bg.graphics.lineStyle(1.8, 0xD4D9E2, 0.95, true);
            bg.graphics.beginGradientFill(GradientType.LINEAR, [0xFFFFFF, 0xF4F6F9], [0.98, 0.98], [0, 255], bgMat);
            bg.graphics.drawRoundRect(left, top, boxW, boxH, radius, radius);
            bg.graphics.endFill();
            
            // Pointer triangle at x = 0
            bg.graphics.lineStyle(1.8, 0xD4D9E2, 0.95, true);
            bg.graphics.beginFill(0xF4F6F9, 1.0);
            bg.graphics.moveTo(-9, top + boxH);
            bg.graphics.lineTo(0, top + boxH + 11);
            bg.graphics.lineTo(9, top + boxH);
            bg.graphics.endFill();
            
            // Erase dividing border line across base of pointer
            bg.graphics.lineStyle(2.4, 0xF4F6F9, 1.0);
            bg.graphics.moveTo(-8, top + boxH);
            bg.graphics.lineTo(8, top + boxH);
         }
         
         var curY:Number = top + b.padY;
         if(b.hasName && b.nameSprite != null)
         {
            b.nameSprite.x = left + b.padX;
            b.nameSprite.y = curY;
            curY += b.nameH + 8;
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
            
            // Typewriter effect (35 characters per second) & dynamic real-time auto-expansion
            if(b.tf != null && b.fullText != null)
            {
               var typeElapsed:Number = now - b.startTime - 100; // start typing 100ms after open starts
               if(typeElapsed > 0)
               {
                  var targetCount:int = Math.min(b.fullText.length, Math.floor(typeElapsed * 0.035));
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
                     
                     var contentW:Number = Math.max(curTextW, b.nameW);
                     b.targetBoxW = Math.max(b.minBoxW, contentW + b.padX * 2);
                     b.targetBoxH = curTextH + b.padY * 2 + (b.hasName ? b.nameH + 8 : 0);
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
