// Estado compartido por ratón, teclado y ambos mandos; no depende del renderizador.
export class Desplegable {
    constructor(catalogos, pageSize = 4) { this.catalogos = catalogos; this.pageSize = pageSize; this.close(); }
    get isOpen() { return this.field !== null; }
    get options() { return this.catalogos[this.field] || []; }
    get page() { return Math.floor(this.index / this.pageSize); }
    get pages() { return Math.max(1, Math.ceil(this.options.length / this.pageSize)); }
    get visible() {
        const start = this.page * this.pageSize;
        return this.options.slice(start, start + this.pageSize).map((option, i) => ({...option, index:start + i}));
    }
    open(field, value) {
        if (!Array.isArray(this.catalogos[field])) return;
        this.field = field; this.index = Math.max(0, this.options.findIndex(option => option.value === value));
    }
    close() { this.field = null; this.index = 0; }
    move(delta) { if (this.options.length) this.index = (this.index + delta + this.options.length) % this.options.length; }
    changePage(delta) {
        this.index = Math.min(this.options.length - 1, Math.max(0, Math.min(this.pages - 1, this.page + delta)) * this.pageSize);
        this.index = Math.max(0, this.index);
    }
    select(index = this.index) {
        const option = this.options[index]; if (!option) return null;
        const selection = {field:this.field, option}; this.close(); return selection;
    }
}
export function hitZone(zones, uv, width = 1440, height = 1080) {
    if (!uv) return null;
    const x = uv.x * width, y = (1 - uv.y) * height;
    return zones.find(z => x >= z.x && x <= z.x + z.w && y >= z.y && y <= z.y + z.h) || null;
}
export function menuLayout(menu) {
    const entries = menu.visible.map((option, row) => ({...option, x:295, y:450 + row * 74, w:850, h:64}));
    return {entries, previous:{x:295,y:770,w:270,h:58}, next:{x:875,y:770,w:270,h:58}};
}
