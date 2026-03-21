declare module "react-cytoscapejs" {
  import type { Core, ElementDefinition, Stylesheet } from "cytoscape";
  import type { CSSProperties, ComponentType } from "react";

  export interface CytoscapeComponentProps {
    className?: string;
    cy?: (core: Core) => void;
    elements?: ElementDefinition[];
    layout?: Record<string, unknown>;
    style?: CSSProperties;
    stylesheet?: Stylesheet[];
    [key: string]: unknown;
  }

  const CytoscapeComponent: ComponentType<CytoscapeComponentProps>;
  export default CytoscapeComponent;
}
