import {Desplegable,hitZone,menuLayout} from './desplegables.mjs';
import {crearSolicitud,Consultas,CAMPOS_API,fechaValida} from './formulario.mjs';
import {vincularProveedores} from './proveedores.mjs';

export class TabletOperaciones {
    constructor({canvas,api,onDirty,onResultados,onNuevaConsulta,politicaCasi}) {
        Object.assign(this,{canvas,api,onDirty,onResultados,onNuevaConsulta,politicaCasi});this.ctx=canvas.getContext('2d');
        this.fields=[
            {id:'cliente',label:'Cliente registrado',kind:'text',value:'',hint:'Nombre del cliente'},
            {id:'fecha_servicio',label:'Fecha del servicio',kind:'date',value:'',hint:'AAAA-MM-DD'},
            {id:'plazo_h',label:'Plazo (horas)',kind:'number',value:'',hint:'Ej. 33'},
            {id:'presupuesto',label:'Presupuesto (miles de COP)',kind:'number',value:'',hint:'Ej. 6.000 = $6.000.000 COP'},
            {id:'peso',label:'Peso (kg)',kind:'number',value:'',hint:'Ej. 24.000 = 24 toneladas'},
            {id:'origen',label:'Ciudad / puerto de origen',kind:'select',value:undefined,hint:'Seleccionar origen'},
            {id:'destino',label:'Ciudad / puerto de destino',kind:'select',value:undefined,hint:'Seleccionar destino'},
            {id:'carga',label:'Tipo de carga',kind:'select',value:undefined,hint:'Seleccionar carga'},
            {id:'vehiculo',label:'Tipo de vehículo',kind:'select',value:null,hint:'Automático (backend)'}
        ];
        this.opciones={};this.menu=new Desplegable(this.opciones);this.consultas=new Consultas(api);this.zones=[];this.hover=new Set();
        this.page=0;this.active=null;this.focus=0;this.keyboardFocus=false;this.catalogos=null;this.catalogLoading=false;this.catalogVersion=0;this.catalogControl=null;
        this.errores={};this.mensaje='Conecta con el backend para cargar las opciones.';this.resultado=null;this.proveedorActual=null;this.detallePage=0;this.discardPage=0;this.casiPage=0;this.dirty=false;
        this.vinculos=new Map();this.mappingErrors=[];this.draw();
    }
    field(id) {return this.fields.find(f=>f.id===id);}
    values() {return Object.fromEntries(this.fields.map(f=>[f.id,f.value]));}
    texto(s,x,y,size=23,color='#16243b',weight=400) {const c=this.ctx;c.fillStyle=color;c.font=`${weight} ${size}px system-ui,sans-serif`;c.textAlign='left';c.fillText(String(s),x,y);}
    rect(x,y,w,h,color) {const c=this.ctx;c.fillStyle=color;c.beginPath();c.roundRect(x,y,w,h,13);c.fill();}
    button(id,label,x,y,w,h,action,enabled=true,primary=false) {
        this.rect(x,y,w,h,enabled?(primary?'#175cde':'#e3ebf7'):'#e3e5e9');this.texto(label,x+14,y+h/2+8,22,enabled?(primary?'white':'#23446d'):'#697587',600);
        if(enabled)this.zones.push({id,x,y,w,h,action});
    }
    wrap(text,width=54) {const words=String(text??'').split(/\s+/),out=[];let line='';for(const w of words){if(line&&(line+' '+w).length>width){out.push(line);line=w;}else line+=(line?' ':'')+w;}if(line)out.push(line);return out;}
    draw() {
        const c=this.ctx;this.zones=[];c.fillStyle='#f5f7fb';c.fillRect(0,0,1440,1080);
        this.texto('GATEX',42,58,32,'#175cde',800);this.texto('OPERACIONES / APOYO A LA DECISIÓN',210,55,20,'#586a82',600);
        this.button('exit','Salir de VR',1190,20,205,55,()=>this.onSalir?.());
        this.button('page0','Datos del envío',42,92,270,56,()=>this.setPage(0));
        this.button('page1','Ruta y carga',327,92,270,56,()=>this.setPage(1));
        this.button('page2','Resultados',612,92,270,56,()=>this.setPage(2),!!this.resultado);
        this.button('connect','Reconectar',990,92,205,56,()=>this.conectar(),!this.catalogLoading&&!this.consultas.ocupado);
        this.texto(this.catalogLoading?'Cargando opciones del servidor…':this.catalogos?(this.catalogos.repositorio.includes('simulad')?'Conectado a datos sintéticos de prueba':'Catálogos obtenidos del backend'):'Sin conexión a los catálogos',42,187,22,'#586a82');
        if(this.page===2)this.drawResultados();else this.drawFields();
        this.drawDescartados();
        const canEvaluate=!!this.catalogos&&!this.catalogLoading&&!this.consultas.ocupado;
        this.button('evaluate',this.consultas.ocupado?'Evaluando…':'Evaluar solicitud',42,606,420,62,()=>this.evaluar(),canEvaluate,true);
        this.button('new','Nueva consulta',477,606,420,62,()=>this.nuevaConsulta());
        const message=this.wrap(this.mensaje,88);message.slice(0,2).forEach((line,i)=>this.texto(line,48,696+i*27,21,this.erroresGlobal?'#9a3412':'#23446d'));
        if(this.active)this.drawKeyboard();
        else {
            this.texto('La evaluación apoya la decisión; no asigna un proveedor.',48,837,22,'#586a82');
            if(this.mappingErrors.length){this.wrap('Revisa la asociación: '+this.mappingErrors.join(' · '),84).slice(0,3).forEach((line,i)=>this.texto(line,48,880+i*25,19,'#9a3412'));}
            if(this.resultado&&this.dirty)this.texto('Resultado anterior: el formulario cambió. Evalúa para actualizar.',48,795,22,'#9a3412');
        }
        if(this.menu.isOpen)this.drawMenu();
        this.focus=Math.min(this.focus,Math.max(0,this.zones.length-1));
        for(const z of this.zones)if(this.hover.has(z.id)||(this.keyboardFocus&&z===this.zones[this.focus])){c.strokeStyle='#175cde';c.lineWidth=5;c.strokeRect(z.x+3,z.y+3,z.w-6,z.h-6);}
        this.onDirty();
    }
    drawFields() {
        const list=this.page===0?this.fields.slice(0,5):this.fields.slice(5);
        list.forEach((f,i)=>{
            const x=42+(i%2)*452,y=214+Math.floor(i/2)*121,w=425;
            this.texto(f.label,x,y+22,22,'#334760',600);this.rect(x,y+33,w,58,this.active===f.id?'#dbe9ff':'white');
            const option=this.opciones[f.id]?.find(o=>o.value===f.value),label=option?.label??(f.value??f.hint);
            const c=this.ctx;c.save();c.beginPath();c.rect(x+10,y+35,w-55,54);c.clip();this.texto(label||f.hint,x+14,y+72,22,f.value!==undefined&&f.value!==''?'#16243b':'#738299');c.restore();
            const disabled=f.kind==='select'&&this.catalogLoading;
            if(f.kind==='select')this.texto('▾',x+w-35,y+72,24,'#175cde');
            if(!disabled)this.zones.push({id:'field-'+f.id,x,y:y+33,w,h:58,action:()=>this.openField(f.id)});
            if(this.errores[f.id])this.texto(this.errores[f.id].slice(0,53),x,y+112,16,'#b42318');
        });
        if(this.page===0)this.button('clients','Ver clientes registrados',496,490,400,50,()=>this.openMenu('cliente'),!!this.catalogos&&!this.catalogLoading);
    }
    setPage(page) {this.page=page;this.active=null;this.menu.close();this.focus=0;this.keyboardFocus=false;this.draw();}
    openField(id) {
        const field=this.field(id);if(field.kind==='select'){this.openMenu(id);return;}
        this.menu.close();this.active=id;this.keyboardFocus=false;this.draw();
    }
    openMenu(id) {
        if(!this.catalogos){this.mensaje='No hay un catálogo cargado. Pulsa Reconectar.';this.draw();return;}
        if(id==='destino'&&!this.field('origen').value){this.mensaje='Selecciona primero un origen.';this.draw();return;}
        if(!this.opciones[id])this.opciones[id]=[];
        if(this.menu.field===id)this.menu.close();else this.menu.open(id,this.field(id).value);
        this.active=null;this.keyboardFocus=false;this.draw();
    }
    drawMenu() {
        const c=this.ctx;c.fillStyle='rgba(14,27,48,.50)';c.fillRect(0,0,1440,1080);this.rect(260,330,920,545,'white');
        this.texto(this.field(this.menu.field).label,295,383,30,'#16243b',700);this.texto('Opciones recibidas de la API',295,420,20,'#586a82');this.zones=[];
        for(const o of menuLayout(this.menu).entries)this.button('option-'+o.index,o.label,o.x,o.y,o.w,o.h,()=>this.choose(o.index),true,false);
        if(!this.menu.options.length)this.texto('No hay opciones para esta selección.',295,493,24);
        if(this.menu.page>0)this.button('previous','Anterior',295,770,270,58,()=>{this.menu.changePage(-1);this.draw();});
        if(this.menu.page<this.menu.pages-1)this.button('next-page','Siguiente',875,770,270,58,()=>{this.menu.changePage(1);this.draw();});
        this.texto(`${this.menu.page+1} / ${this.menu.pages}`,672,807,24,'#586a82');
        this.button('close-menu','Cerrar',970,348,175,54,()=>{this.menu.close();this.draw();});
        this.focus=Math.max(0,this.zones.findIndex(z=>z.id==='option-'+this.menu.index));
        this.zones.push({id:'dismiss',x:0,y:0,w:1440,h:1080,action:()=>{this.menu.close();this.draw();}});
    }
    choose(index) {
        const selection=this.menu.select(index);if(!selection)return;const field=this.field(selection.field);
        field.value=selection.field==='cliente'?selection.option.label:selection.option.value;this.consultas.cancelar();this.errores[field.id]=null;this.dirty=true;this.draw();
        if(field.id==='origen')this.conectar();
    }
    edit(key) {
        if(!this.active)return;const f=this.field(this.active);this.consultas.cancelar();
        if(key==='DEL')f.value=Array.from(f.value).slice(0,-1).join('');
        else if(key==='DONE'){const id=this.active;this.active=null;if(id==='fecha_servicio'&&this.catalogos)this.conectar();}
        else if(key==='NEXT'){const index=(this.fields.indexOf(f)+1)%this.fields.length;const next=this.fields[index];this.page=index>=5?1:0;this.active=null;this.openField(next.id);return;}
        else if(String(f.value).length<90)f.value+=key;
        this.errores[f.id]=null;this.dirty=true;this.draw();
    }
    drawKeyboard() {
        this.rect(42,735,1353,300,'#f5f7fb');
        const rows=['1234567890','QWERTYUIOP','ASDFGHJKLÑ','ZXCVBNM.-/'];
        rows.forEach((row,r)=>Array.from(row).forEach((key,col)=>this.button('key-'+key,key,42+col*96,737+r*53,88,46,()=>this.edit(key))));
        this.button('space','Espacio',42,957,300,52,()=>this.edit(' '));this.button('comma',',',357,957,95,52,()=>this.edit(','));
        this.button('delete','Borrar',467,957,220,52,()=>this.edit('DEL'));this.button('next','Siguiente',702,957,260,52,()=>this.edit('NEXT'));this.button('done','Listo',977,957,418,52,()=>this.edit('DONE'),true,true);
    }
    async conectar() {
        const version=++this.catalogVersion;this.catalogControl?.abort();this.catalogControl=new AbortController();this.catalogLoading=true;this.menu.close();this.draw();
        try {
            const catalogos=await this.api.catalogos(this.field('origen').value||'',fechaValida(this.field('fecha_servicio').value)?this.field('fecha_servicio').value:'',this.catalogControl.signal);
            if(version!==this.catalogVersion)return;
            if(!catalogos||typeof catalogos.repositorio!=='string')throw new Error('El servidor no devolvió el contrato de catálogos esperado. Actualiza el backend.');
            for(const key of ['origenes','destinos','rutas','clientes','tipos_carga','tipos_vehiculo','proveedores'])if(!Array.isArray(catalogos[key]))throw new Error('El endpoint /catalogos no devuelve '+key+'. Actualiza el backend.');
            this.catalogos=catalogos;const mapping=vincularProveedores(catalogos.proveedores);this.vinculos=mapping.porId;this.mappingErrors=mapping.errores;
            const asOptions=list=>list.map(o=>({value:o.id,label:o.nombre}));
            Object.assign(this.opciones,{cliente:asOptions(catalogos.clientes),origen:asOptions(catalogos.origenes),destino:asOptions(catalogos.destinos),carga:asOptions(catalogos.tipos_carga),vehiculo:[{value:null,label:'Automático (backend)'},...asOptions(catalogos.tipos_vehiculo)]});
            const invalid=[];for(const id of ['origen','destino','carga','vehiculo']){const f=this.field(id);if(f.value!==undefined&&!this.opciones[id].some(o=>o.value===f.value)){f.value=undefined;invalid.push(f.label);this.dirty=true;}}
            this.mensaje=invalid.length?'Selecciona de nuevo: '+invalid.join(', '):'Catálogos cargados. La disponibilidad final se evalúa al enviar.';this.erroresGlobal=false;
        } catch(error){if(version!==this.catalogVersion||error.name==='AbortError')return;this.catalogos=null;this.mensaje=error.status===404?'Falta GET /catalogos en el servidor. Instala la actualización del backend.':error.message;this.erroresGlobal=true;}
        finally {if(version===this.catalogVersion){this.catalogLoading=false;this.draw();}}
    }
    async evaluar() {
        if(!this.catalogos||this.catalogLoading||this.consultas.ocupado)return;
        if(!['panel','arriba'].includes(this.politicaCasi)){this.mensaje='Falta confirmar cómo presentar los casi elegibles.';this.draw();return;}
        if(this.mappingErrors.length){this.mensaje='La asociación de proveedores y tarjetas está incompleta. Revisa los nombres del catálogo.';this.erroresGlobal=true;this.draw();return;}
        const validation=crearSolicitud(this.values(),this.catalogos);this.errores=validation.errores;
        if(Object.keys(this.errores).length){this.page=this.fields.findIndex(f=>this.errores[f.id])<5?0:1;this.mensaje='Revisa los campos señalados. No se envió la solicitud.';this.draw();return;}
        this.active=null;this.menu.close();this.mensaje='Evaluando solicitud…';this.erroresGlobal=false;
        const pending=this.consultas.evaluar(validation.datos);this.draw();
        try {
            const evaluation=await pending;if(!evaluation)return;
            this.onResultados(evaluation,this.vinculos,this.politicaCasi);
            this.resultado=evaluation;this.dirty=false;this.page=2;this.detallePage=0;this.discardPage=0;this.casiPage=0;this.proveedorActual=evaluation.candidatos[0]?.proveedor_id||null;
            this.mensaje=evaluation.sin_candidatos?'No hay proveedores adecuados. Revisa descartados y qué podría flexibilizarse.':`${evaluation.candidatos.length} candidatos disponibles. La decisión final es del operador.`;
        } catch(error){this.mensaje=error.message;this.erroresGlobal=true;for(const item of error.errores||[]){const field=CAMPOS_API[item.campo];if(field)this.errores[field]=item.mensaje;}if(Object.keys(this.errores).length)this.page=this.fields.findIndex(f=>this.errores[f.id])<5?0:1;}
        finally {this.draw();}
    }
    nuevaConsulta() {
        this.consultas.cancelar();this.catalogVersion++;this.catalogControl?.abort();this.catalogLoading=false;
        this.menu.close();this.active=null;this.resultado=null;this.proveedorActual=null;this.detallePage=0;this.discardPage=0;this.casiPage=0;this.page=0;this.errores={};this.dirty=false;
        for(const field of this.fields)field.value=field.kind==='select'?(field.id==='vehiculo'?null:undefined):'';
        this.onNuevaConsulta();this.mensaje='Nueva consulta: las tarjetas vuelven a sus posiciones originales.';this.erroresGlobal=false;this.draw();this.conectar();
    }
    seleccionarProveedor(id) {if(!this.resultado?.candidatos.some(p=>p.proveedor_id===id))return;this.proveedorActual=id;this.detallePage=0;this.page=2;this.active=null;this.menu.close();this.draw();}
    drawResultados() {
        const r=this.resultado;if(!r)return;
        const items=r.candidatos,index=Math.max(0,items.findIndex(p=>p.proveedor_id===this.proveedorActual)),p=items[index];
        this.texto('Solicitud '+r.solicitud_id+(this.dirty?' · resultado anterior':''),42,238,26,'#16243b',700);
        if(!p){this.texto('No hay proveedores adecuados.',42,291,29,'#9a3412',700);this.texto('Revisa los motivos y las alternativas del panel derecho.',42,338,22);return;}
        this.texto(p.nombre,42,282,26,'#175cde',700);
        const money=n=>n==null?'No disponible':new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',maximumFractionDigits:0}).format(n);
        const rows=[`Vehículo: ${p.vehiculos.tipo} · Cantidad: ${p.vehiculos.cantidad}`,`Costo: ${money(p.costo_cop)} · Profit esperado: ${money(p.profit.esperado_cop)}`,`Profit P10: ${money(p.profit.p10_cop)} · Margen: ${p.profit.margen_pct==null?'No disponible':p.profit.margen_pct+' %'}`,`Tránsito P50: ${p.tiempo_h.p50} h · P90: ${p.tiempo_h.p90} h`,`A tiempo: ${(p.tiempo_h.prob_a_tiempo*100).toFixed(1)} % · Incidente: ${(p.prob_incidente*100).toFixed(1)} %`,`Desempeño: ${p.desempeno.valor} · Confianza: ${p.confianza.valor} (${p.confianza.nivel})`,p.explicacion,...p.riesgos.map(s=>'Riesgo: '+s),...p.avisos.map(s=>'Aviso: '+s)].flatMap(s=>this.wrap(s,75));
        const pages=Math.max(1,Math.ceil(rows.length/7));this.detallePage=Math.min(this.detallePage,pages-1);
        rows.slice(this.detallePage*7,this.detallePage*7+7).forEach((s,i)=>this.texto(s,42,325+i*29,21));
        this.button('detail-prev','Texto anterior',42,540,210,48,()=>{this.detallePage--;this.draw();},this.detallePage>0);
        this.button('detail-next','Más información',267,540,245,48,()=>{this.detallePage++;this.draw();},this.detallePage<pages-1);
        this.button('provider-prev','‹',625,540,70,48,()=>this.seleccionarProveedor(items[(index-1+items.length)%items.length].proveedor_id),items.length>1);
        this.texto(`${index+1} / ${items.length}`,720,572,22);
        this.button('provider-next','›',820,540,70,48,()=>this.seleccionarProveedor(items[(index+1)%items.length].proveedor_id),items.length>1);
    }
    drawDescartados() {
        this.rect(970,210,425,366,'white');this.texto('Descartados',990,250,27,'#16243b',700);
        const r=this.resultado;
        const lines=r?r.cancelados.flatMap(p=>[p.nombre,...p.razones.flatMap(reason=>this.wrap(reason.mensaje,33))]):['Sin evaluación todavía.'];
        if(r&&!lines.length)lines.push('No hay descartados.');
        const pages=Math.max(1,Math.ceil(lines.length/8));this.discardPage=Math.min(this.discardPage,pages-1);
        lines.slice(this.discardPage*8,this.discardPage*8+8).forEach((s,i)=>this.texto(s,990,287+i*29,19));
        this.button('discard-prev','‹',990,526,80,40,()=>{this.discardPage--;this.draw();},this.discardPage>0);this.texto(`${this.discardPage+1}/${pages}`,1140,555,19);
        this.button('discard-next','›',1295,526,80,40,()=>{this.discardPage++;this.draw();},this.discardPage<pages-1);
        if(r?.casi_elegibles.length&&!this.active){
            this.rect(970,600,425,395,'#fff1d6');this.texto('Casi elegibles',990,641,25,'#704512',700);
            const rows=r.casi_elegibles.flatMap(p=>[p.nombre,...this.wrap(p.razon.mensaje,33),...this.wrap(p.flexibilizar,33)]);
            const count=Math.max(1,Math.ceil(rows.length/9));this.casiPage=Math.min(this.casiPage,count-1);
            rows.slice(this.casiPage*9,this.casiPage*9+9).forEach((s,i)=>this.texto(s,990,678+i*28,19,'#704512'));
            this.button('casi-prev','‹',990,941,80,40,()=>{this.casiPage--;this.draw();},this.casiPage>0);this.texto(`${this.casiPage+1}/${count}`,1140,970,19);
            this.button('casi-next','›',1295,941,80,40,()=>{this.casiPage++;this.draw();},this.casiPage<count-1);
        }
    }
    hit(uv) {return hitZone(this.zones,uv);}
    activate(uv) {const z=this.hit(uv);if(z)z.action();else if(this.menu.isOpen){this.menu.close();this.draw();}}
    setHover(ids) {const next=new Set(ids.filter(Boolean));if([...next].sort().join('|')===[...this.hover].sort().join('|'))return;this.hover=next;this.draw();}
    scroll(delta) {if(this.menu.isOpen){this.menu.changePage(delta>0?1:-1);this.draw();}}
    key(event) {
        if(event.ctrlKey||event.metaKey||event.altKey)return;
        if(this.menu.isOpen){
            if(['Escape','Enter',' ','Tab','ArrowDown','ArrowUp','ArrowRight','ArrowLeft','PageDown','PageUp','Home','End'].includes(event.key))event.preventDefault();
            if(event.key==='Escape'){this.menu.close();this.draw();return;}
            if(event.key==='Enter'||event.key===' '){if(!event.repeat)this.choose(this.menu.index);return;}
            if(event.key==='ArrowDown'||event.key==='ArrowRight'||event.key==='Tab')this.menu.move(event.shiftKey?-1:1);
            else if(event.key==='ArrowUp'||event.key==='ArrowLeft')this.menu.move(-1);
            else if(event.key==='PageDown')this.menu.changePage(1);else if(event.key==='PageUp')this.menu.changePage(-1);
            else if(event.key==='Home')this.menu.index=0;else if(event.key==='End')this.menu.index=Math.max(0,this.menu.options.length-1);
            this.keyboardFocus=true;this.draw();return;
        }
        if(['Tab','ArrowRight','ArrowLeft','Enter','Backspace','Escape'].includes(event.key))event.preventDefault();
        if(event.key==='Tab'||event.key==='ArrowRight'||event.key==='ArrowLeft'){this.focus=(this.focus+((event.shiftKey||event.key==='ArrowLeft')?-1:1)+this.zones.length)%this.zones.length;this.keyboardFocus=true;this.draw();}
        else if(event.key==='Enter'){if(!event.repeat)this.zones[this.focus]?.action();}
        else if(event.key==='Escape'){this.active=null;this.draw();}
        else if(event.key==='Backspace')this.edit('DEL');else if(event.key.length===1){event.preventDefault();this.edit(event.key);}
    }
}




