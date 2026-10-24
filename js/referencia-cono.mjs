const sub=(a,b)=>a.map((x,i)=>x-b[i]);
const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const length=v=>Math.hypot(...v);

export function identificarCono(vertices) {
    if(!vertices.length)throw new Error('Usuario no contiene vértices.');
    const alcance=Math.max(...[0,1,2].map(k=>Math.max(...vertices.map(p=>p[k]))-Math.min(...vertices.map(p=>p[k]))));
    if(alcance<=1e-8)throw new Error('Usuario tiene geometría degenerada.');
    const tolerancia=alcance*1e-5;
    const unique=new Map();
    for(const p of vertices)unique.set(p.map(v=>Math.round(v/tolerancia)).join(','),p);
    const puntos=[...unique.values()];
    if(puntos.length<5||puntos.length>512)throw new Error('Usuario no es un cono simple identificable; revisa el objeto en Blender.');
    const candidatos=[];
    for(let i=0;i<puntos.length;i++) {
        const base=puntos.filter((_,j)=>j!==i),a=base[0];
        const b=base.reduce((best,p)=>length(sub(p,a))>length(sub(best,a))?p:best,a);
        const c=base.reduce((best,p)=>length(cross(sub(b,a),sub(p,a)))>length(cross(sub(b,a),sub(best,a)))?p:best,a);
        let normal=cross(sub(b,a),sub(c,a));const magnitude=length(normal);if(magnitude<tolerancia*tolerancia)continue;
        normal=normal.map(x=>x/magnitude);
        if(base.some(p=>Math.abs(dot(sub(p,a),normal))>tolerancia))continue;
        const centro=[0,1,2].map(k=>base.reduce((sum,p)=>sum+p[k],0)/base.length);
        const eje=sub(puntos[i],centro),altura=Math.abs(dot(eje,normal));
        if(altura<tolerancia||length(cross(eje,normal))>tolerancia*4)continue;
        const radios=base.map(p=>length(sub(p,centro))),r=radios.reduce((s,v)=>s+v,0)/radios.length;
        if(r<tolerancia||radios.some(v=>Math.abs(v-r)>tolerancia*4))continue;
        candidatos.push({punta:puntos[i],base:centro});
    }
    if(candidatos.length!==1)throw new Error('No se pudo distinguir una punta y una base circular únicas en Usuario.');
    return candidatos[0]; // Deducción geométrica, sin fijar X, Y o Z como eje del cono.
}
