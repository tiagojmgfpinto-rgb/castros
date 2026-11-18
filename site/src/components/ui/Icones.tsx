import { TIPOLOGIAS, type Tipologia } from "../../lib/tipologias";

// Desenhos pequenos da interface: marca (roda com tríscele), símbolo castrejo de cada tipologia e rosa dos ventos.

const BRACO = "M0 0c0-6.2 5.1-9.8 9.9-8.1 4 1.4 4.8 6.2 2.1 8.6";

/**
 * Marca: roda com o tríscele castrejo, no lugar do escudo com a torre dos Castelos (mesmo tamanho e cores).
 * O aro de contas lembra as cordas entrançadas das pedras decoradas de Briteiros e Sanfins.
 */
export function Escudo() {
  return (
    <svg className="escudo" viewBox="0 0 48 56" aria-hidden="true">
      <circle className="e-campo" cx="24" cy="28" r="21.5" />
      <g className="e-contas">
        {Array.from({ length: 24 }, (_, i) => {
          const a = (i / 24) * Math.PI * 2;
          return <circle key={i} cx={(24 + Math.cos(a) * 18.2).toFixed(2)} cy={(28 + Math.sin(a) * 18.2).toFixed(2)} r="0.95" />;
        })}
      </g>
      <g className="e-triscele" transform="translate(24 28.6)">
        {[0, 120, 240].map((r) => <path key={r} transform={`rotate(${r})`} d={BRACO} />)}
      </g>
      <circle className="e-centro" cx="24" cy="28.6" r="2" />
    </svg>
  );
}

type Forma = "casa" | "citania" | "pedra-formosa" | "triskele";

const traco = { fill: "var(--papel-claro)", stroke: "currentColor", strokeWidth: 1.3, strokeLinejoin: "round" as const };

/** Casa castreja em alçado: parede circular com porta e cobertura cónica de colmo. */
const Casa = ({ x, y, k }: { x: number; y: number; k: number }) => (
  <g transform={`translate(${x} ${y}) scale(${k})`}>
    <path {...traco} strokeWidth={1.3 / k} d="M-5.5 0v-7.2h11V0z" />
    <path {...traco} strokeWidth={1.3 / k} d="M-7.6 -6.6L0 -17.4L7.6 -6.6z" />
    <path d="M-1.7 0v-3.4a1.7 1.7 0 0 1 3.4 0V0z" fill="currentColor" />
    <path d="M-4.2 -9.4h8.4M-2.4 -12.6h4.8" stroke="currentColor" strokeWidth={0.8 / k} />
  </g>
);

export function IconeTipo({ tipo }: { tipo: Tipologia }) {
  const f = TIPOLOGIAS[tipo]?.forma as Forma;
  return (
    <span className="icone-tipo" aria-hidden="true">
      <svg viewBox="0 0 24 27" focusable="false">
        {f === "casa" && (
          <>
            <Casa x={12} y={26} k={1.25} />
            <circle cx="12" cy="3.6" r="1.3" fill="var(--gules)" />
          </>
        )}
        {f === "citania" && (
          <>
            <path {...traco} d="M1.3 26c0-4.2 4.8-6.6 10.7-6.6s10.7 2.4 10.7 6.6z" />
            <Casa x={6.8} y={24.4} k={0.62} />
            <Casa x={17.2} y={24.4} k={0.62} />
            <Casa x={12} y={21.4} k={0.8} />
          </>
        )}
        {f === "pedra-formosa" && (
          <>
            <path {...traco} d="M3.5 26V11.5L12 3l8.5 8.5V26z" />
            <path d="M8.8 26v-4.6a3.2 3.2 0 0 1 6.4 0V26z" fill="currentColor" />
            <g fill="none" stroke="currentColor" strokeWidth="1">
              <circle cx="8.6" cy="14" r="2" />
              <circle cx="15.4" cy="14" r="2" />
              <circle cx="12" cy="9" r="1.7" />
            </g>
          </>
        )}
        {f === "triskele" && (
          <>
            <circle {...traco} cx="12" cy="14.5" r="10.5" />
            <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" transform="translate(12 14.8) scale(0.58)">
              {[0, 120, 240].map((r) => <path key={r} transform={`rotate(${r})`} d={BRACO} />)}
            </g>
            <circle cx="12" cy="14.8" r="1.4" fill="var(--gules)" />
          </>
        )}
      </svg>
    </span>
  );
}

/** Rosa dos ventos de oito pontas; o norte a vermelho. Roda com o rumo da câmara. */
export function Rosa({ rumo, onClick }: { rumo: number; onClick: () => void }) {
  const ponta = (a: number, comprida: boolean) => {
    const r = comprida ? 27 : 17;
    const w = comprida ? 4.6 : 3.4;
    const rad = (a * Math.PI) / 180;
    const [sx, sy] = [Math.sin(rad), -Math.cos(rad)];
    const [px, py] = [-sy, sx];
    return `M${32 + sx * r} ${32 + sy * r}L${32 + px * w} ${32 + py * w}L32 32L${32 - px * w} ${32 - py * w}Z`;
  };
  return (
    <button className="rosa-botao" type="button" title="Orientar a norte" aria-label="Orientar o mapa a norte" onClick={onClick}>
      <svg className="rosa" viewBox="0 0 64 64" aria-hidden="true">
        <circle className="r-aro" cx="32" cy="32" r="30" />
        <circle className="r-aro2" cx="32" cy="32" r="24" />
        <g style={{ transform: `rotate(${-rumo}deg)`, transformOrigin: "32px 32px" }}>
          {[45, 135, 225, 315].map((a) => <path key={a} className="r-sec" d={ponta(a, false)} />)}
          <path className="r-eo" d={ponta(90, true)} />
          <path className="r-eo" d={ponta(270, true)} />
          <path className="r-s" d={ponta(180, true)} />
          <path className="r-n" d={ponta(0, true)} />
          <text className="r-letra" x="32" y="3.2" textAnchor="middle">N</text>
        </g>
        <circle className="r-eixo" cx="32" cy="32" r="2.6" />
      </svg>
    </button>
  );
}
