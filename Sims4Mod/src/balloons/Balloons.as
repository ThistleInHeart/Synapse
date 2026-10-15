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
         
         this.createBalloon(simId, balloonType, simName, text, duration);
      }
      
      private function createBalloon(simId:String, balloonType:String, simName:String, text:String, durationSec:Number):void
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
         var padX:Number = isThought ? 22 : 16;
         var padY:Number = isThought ? 16 : 12;
         var radius:Number = isThought ? 22 : 16;
         
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
         
         // Temporarily set full text to measure final dimensions accurately
         tf.text = text;
         if(tf.textWidth + 8 < maxTextWidth)
         {
            tf.width = tf.textWidth + 8;
         }
         var actualTextW:Number = tf.width;
         var actualTextH:Number = tf.height;
         
         // Reset text to empty string for typewriter effect
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
            
            nameW = ntf.textWidth + 14;
            nameH = ntf.textHeight + 4;
            
            var nMat:Matrix = new Matrix();
            nMat.createGradientBox(nameW, nameH, Math.PI / 2, 0, 0);
            
            var nColorTop:uint = (balloonType == "thought") ? 0x8E65FA : 0x7A5CFA;
            var nColorBot:uint = (balloonType == "thought") ? 0x6E48C9 : 0x5D3EBC;
            nameSprite.graphics.beginGradientFill(GradientType.LINEAR, [nColorTop, nColorBot], [1, 1], [0, 255], nMat);
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
         var tail:Shape = null;
         var bgMat:Matrix = new Matrix();
         bgMat.createGradientBox(boxW, boxH, Math.PI / 2, left, top);
         
         var borderW:Number = 1.8;
         
         if(isThought)
         {
            var bHalf:Number = boxH / 2;
            var cornerR:Number = Math.min(18, bHalf * 0.5);
            var lobeR:Number = Math.max(12, Math.min(17, bHalf * 0.36));
            
            // Build list of perimeter lobes
            var lobesX:Array = [];
            var lobesY:Array = [];
            var lobesR:Array = [];
            
            // 4 corners
            var cOff:Number = cornerR * 0.25;
            lobesX.push(left + cornerR - cOff);
            lobesY.push(top + cornerR - cOff);
            lobesR.push(lobeR * 1.15);
            
            lobesX.push(left + boxW - cornerR + cOff);
            lobesY.push(top + cornerR - cOff);
            lobesR.push(lobeR * 1.12);
            
            lobesX.push(left + boxW - cornerR + cOff);
            lobesY.push(top + boxH - cornerR + cOff);
            lobesR.push(lobeR * 1.14);
            
            lobesX.push(left + cornerR - cOff);
            lobesY.push(top + boxH - cornerR + cOff);
            lobesR.push(lobeR * 1.1);
            
            // Top edge lobes
            var topW:Number = boxW - cornerR * 2;
            var nTop:int = Math.max(1, Math.round(topW / (lobeR * 2.2)));
            for(var kt:int = 1; kt <= nTop; kt++)
            {
               var fracT:Number = kt / (nTop + 1);
               lobesX.push(left + cornerR + topW * fracT);
               lobesY.push(top + lobeR * 0.12);
               lobesR.push(lobeR * (kt % 2 == 1 ? 1.18 : 1.05));
            }
            
            // Bottom edge lobes
            var botW:Number = boxW - cornerR * 2;
            var nBot:int = Math.max(1, Math.round(botW / (lobeR * 2.2)));
            for(var kb:int = 1; kb <= nBot; kb++)
            {
               var fracB:Number = kb / (nBot + 1);
               lobesX.push(left + cornerR + botW * fracB);
               lobesY.push(top + boxH - lobeR * 0.12);
               lobesR.push(lobeR * (kb % 2 == 0 ? 1.15 : 1.02));
            }
            
            // Side edges (left & right)
            var sideH:Number = boxH - cornerR * 2;
            var nSide:int = Math.max(1, Math.round(sideH / (lobeR * 2.0)));
            for(var ks:int = 1; ks <= nSide; ks++)
            {
               var fracS:Number = ks / (nSide + 1);
               var pyS:Number = top + cornerR + sideH * fracS;
               lobesX.push(left + lobeR * 0.12);
               lobesY.push(pyS);
               lobesR.push(lobeR * 1.08);
               
               lobesX.push(left + boxW - lobeR * 0.12);
               lobesY.push(pyS);
               lobesR.push(lobeR * 1.06);
            }
            
            // Center inner core rect
            var coreInset:Number = 7;
            var coreLeft:Number = left + coreInset;
            var coreTop:Number = top + coreInset;
            var coreW:Number = boxW - coreInset * 2;
            var coreH:Number = boxH - coreInset * 2;
            var coreR:Number = 14;
            
            // PASS 1: Unified Outer Border Silhouette (Solid Border Fill)
            bg.graphics.beginFill(0xCBD1DC, 0.96);
            bg.graphics.drawRoundRect(coreLeft - borderW, coreTop - borderW, coreW + borderW * 2, coreH + borderW * 2, coreR + borderW * 2, coreR + borderW * 2);
            for(var i1:int = 0; i1 < lobesX.length; i1++)
            {
               bg.graphics.drawCircle(lobesX[i1], lobesY[i1], lobesR[i1] + borderW);
            }
            bg.graphics.endFill();
            
            // PASS 2: Unified Inner Fill (Soft Gradient White to Pale Blue-Gray)
            bg.graphics.beginGradientFill(GradientType.LINEAR, [0xFFFFFF, 0xF6F8FC], [0.98, 0.98], [0, 255], bgMat);
            bg.graphics.drawRoundRect(coreLeft, coreTop, coreW, coreH, coreR, coreR);
            for(var i2:int = 0; i2 < lobesX.length; i2++)
            {
               bg.graphics.drawCircle(lobesX[i2], lobesY[i2], lobesR[i2]);
            }
            bg.graphics.endFill();
            
            // Descending Thought Bubble Tail (3 cleanly spaced bubbles pointing to head)
            var tailX:Array = [-8, -4, -1];
            var tailY:Array = [top + boxH + 13, top + boxH + 24, top + boxH + 33];
            var tailR:Array = [5.5, 3.8, 2.2];
            
            tail = new Shape();
            // Tail Border Pass
            tail.graphics.beginFill(0xCBD1DC, 0.96);
            for(var tb1:int = 0; tb1 < 3; tb1++)
            {
               tail.graphics.drawCircle(tailX[tb1], tailY[tb1], tailR[tb1] + borderW);
            }
            tail.graphics.endFill();
            // Tail Fill Pass
            tail.graphics.beginFill(0xFFFFFF, 0.98);
            for(var tb2:int = 0; tb2 < 3; tb2++)
            {
               tail.graphics.drawCircle(tailX[tb2], tailY[tb2], tailR[tb2]);
            }
            tail.graphics.endFill();
         }
         else
         {
            // Speech Card Body (Pass 1: Border with fused tail triangle)
            bg.graphics.beginFill(0xDADEE5, 0.96);
            bg.graphics.drawRoundRect(left - borderW, top - borderW, boxW + borderW * 2, boxH + borderW * 2, radius + borderW * 2, radius + borderW * 2);
            bg.graphics.moveTo(-10 - borderW, top + boxH - 1);
            bg.graphics.lineTo(0, top + boxH + 11 + borderW);
            bg.graphics.lineTo(10 + borderW, top + boxH - 1);
            bg.graphics.endFill();
            
            // Speech Card Body (Pass 2: Inner Fill with fused tail triangle)
            bg.graphics.beginGradientFill(GradientType.LINEAR, [0xFFFFFF, 0xF4F6F9], [0.98, 0.98], [0, 255], bgMat);
            bg.graphics.drawRoundRect(left, top, boxW, boxH, radius, radius);
            bg.graphics.moveTo(-10, top + boxH - 1);
            bg.graphics.lineTo(0, top + boxH + 11);
            bg.graphics.lineTo(10, top + boxH - 1);
            bg.graphics.endFill();
         }
         
         body.addChild(bg);
         if(tail != null)
         {
            body.addChild(tail);
         }
         
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
            "tf": tf,
            "fullText": text,
            "typedChars": 0,
            "type": balloonType,
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
            
            // Typewriter effect (35 characters per second)
            if(b.tf != null && b.fullText != null)
            {
               var typeElapsed:Number = now - b.startTime - 120; // start typing 120ms after open starts
               if(typeElapsed > 0)
               {
                  var targetCount:int = Math.min(b.fullText.length, Math.floor(typeElapsed * 0.035));
                  if(targetCount != b.typedChars)
                  {
                     b.typedChars = targetCount;
                     (b.tf as TextField).text = b.fullText.substr(0, targetCount);
                  }
               }
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
