#!/bin/sh
F="$1"
[ -f "$F" ] || { echo "NO FILE"; exit 1; }
cp -f "$F" "$F.bak" || exit 1
cat > /tmp/kzl.txt <<'LAY'
<CALayer id="#301" allowsEdgeAntialiasing="1" allowsGroupOpacity="1" bounds="0 0 150 150" contentsFormat="RGBA8" hidden="0" name="d3" opacity="0" position="77.2 74.8" transform="scale(0.578, 0.578, 1)"><contents type="CGImage" src="3.png"/></CALayer>
<CALayer id="#302" allowsEdgeAntialiasing="1" allowsGroupOpacity="1" bounds="0 0 150 150" contentsFormat="RGBA8" hidden="0" name="d2" opacity="0" position="77.2 74.8" transform="scale(0.578, 0.578, 1)"><contents type="CGImage" src="2.png"/></CALayer>
<CALayer id="#303" allowsEdgeAntialiasing="1" allowsGroupOpacity="1" bounds="0 0 150 150" contentsFormat="RGBA8" hidden="0" name="d1" opacity="0" position="77.2 74.8" transform="scale(0.578, 0.578, 1)"><contents type="CGImage" src="1.png"/></CALayer>
LAY
A='<LKStateSetValue targetId="#301" keyPath="opacity"><value type="integer" value="1"/></LKStateSetValue><LKStateSetValue targetId="#302" keyPath="opacity"><value type="integer" value="0"/></LKStateSetValue><LKStateSetValue targetId="#303" keyPath="opacity"><value type="integer" value="0"/></LKStateSetValue>'
B='<LKStateSetValue targetId="#301" keyPath="opacity"><value type="integer" value="0"/></LKStateSetValue><LKStateSetValue targetId="#302" keyPath="opacity"><value type="integer" value="1"/></LKStateSetValue><LKStateSetValue targetId="#303" keyPath="opacity"><value type="integer" value="0"/></LKStateSetValue>'
C='<LKStateSetValue targetId="#301" keyPath="opacity"><value type="integer" value="0"/></LKStateSetValue><LKStateSetValue targetId="#302" keyPath="opacity"><value type="integer" value="0"/></LKStateSetValue><LKStateSetValue targetId="#303" keyPath="opacity"><value type="integer" value="1"/></LKStateSetValue>'
D='<LKStateSetValue targetId="#301" keyPath="opacity"><value type="integer" value="0"/></LKStateSetValue><LKStateSetValue targetId="#302" keyPath="opacity"><value type="integer" value="0"/></LKStateSetValue><LKStateSetValue targetId="#303" keyPath="opacity"><value type="integer" value="0"/></LKStateSetValue>'
awk -v S1="$A" -v S2="$B" -v S3="$C" -v S4="$D" -v LF=/tmp/kzl.txt '
BEGIN{ while((getline l < LF)>0){ n++; LL[n]=l } }
/<LKState name="/ { if(match($0,/name="[^"]*"/)) st=substr($0,RSTART+6,RLENGTH-7) }
{ if(!d && index($0,"<CALayer id=\"#3\"")>0){ for(i=1;i<=n;i++) print LL[i]; d=1 } }
/<elements>/ { print; if(st=="3")print S1; else if(st=="2")print S2; else if(st=="1")print S3; else if(st=="start")print S4; next }
{ print }' "$F" > /tmp/kznew.caml || exit 1
cp -f /tmp/kznew.caml "$F" || exit 1
echo "DONE refs=$(grep -c '#30[123]' "$F")"
