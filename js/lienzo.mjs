// Dibujo e interacción compartidos por la tablet y los paneles flotantes: un canvas de 1440×1080
// con zonas pulsables. Funciona igual con mando, pinch o clic (todos llegan como coordenadas uv).
import {hitZone} from './desplegables.mjs';

export const FILAS_TECLADO=['1234567890','QWERTYUIOP','ASDFGHJKLÑ','ZXCVBNM.-/'];

export class LienzoUI {
    constructor({canvas,onDirty=()=>{}}) {
        this.canvas=canvas;this.ctx=canvas.getContext('2d');this.onDirty=onDirty;
        this.zones=[];this.hover=new Set();this.focus=0;this.keyboardFocus=false;
    }
    texto(s,x,y,size=23,color='#16243b',weight=400) {const c=this.ctx;c.fillStyle=color;c.font=`${weight} ${size}px system-ui,sans-serif`;c.textAlign='left';c.fillText(String(s),x,y);}
    rect(x,y,w,h,color,radio=13) {const c=this.ctx;c.fillStyle=color;c.beginPath();c.roundRect(x,y,w,h,radio);c.fill();}
    // Un botón deshabilitado se dibuja pero no crea zona: no se puede pulsar.
    button(id,label,x,y,w,h,action,enabled=true,primary=false,{size=22,fondo,color}={}) {
        this.rect(x,y,w,h,enabled?(fondo||(primary?'#175cde':'#e3ebf7')):'#e3e5e9');
        this.texto(label,x+14,y+h/2+size*.36,size,enabled?(color||(primary?'white':'#23446d')):'#697587',600);
        if(enabled)this.zones.push({id,x,y,w,h,action});
    }
    wrap(text,width=54) {const words=String(text??'').split(/\s+/),out=[];let line='';for(const w of words){if(line&&(line+' '+w).length>width){out.push(line);line=w;}else line+=(line?' ':'')+w;}if(line)out.push(line);return out;}
    marcarFoco() {
        const c=this.ctx;this.focus=Math.min(this.focus,Math.max(0,this.zones.length-1));
        for(const z of this.zones)if(this.hover.has(z.id)||(this.keyboardFocus&&z===this.zones[this.focus])){c.strokeStyle='#0b1f44';c.lineWidth=6;c.strokeRect(z.x+3,z.y+3,z.w-6,z.h-6);}
    }
    hit(uv) {return hitZone(this.zones,uv);}
    setHover(ids) {const next=new Set(ids.filter(Boolean));if([...next].sort().join('|')===[...this.hover].sort().join('|'))return;this.hover=next;this.draw();}
}

// Teclado en pantalla (4 filas de 10 teclas). Cada interfaz dibuja su propia fila de acciones.
export function dibujarTeclas(ui,x0,y0,onKey,minusculas=false) {
    FILAS_TECLADO.forEach((row,r)=>Array.from(row).forEach((key,col)=>{
        const k=minusculas?key.toLowerCase():key;
        ui.button('key-'+key,k,x0+col*96,y0+r*53,88,46,()=>onKey(k));
    }));
}
