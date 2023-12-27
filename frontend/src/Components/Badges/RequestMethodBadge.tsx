import { Badge } from "mkui/Components/Badge"

export const RequestMethodBadge = ({ method }: { method: string }) => {
  switch (method) {
    case "GET":
      return <Badge color="green">{method}</Badge>
    case "DELETE":
      return <Badge color="red">{method}</Badge>
    case "PUT":
      return <Badge color="yellow">{method}</Badge>
    case "POST":
      return <Badge color="orange">{method}</Badge>
    case "PATCH":
      return <Badge color="purple">{method}</Badge>
    case "OPTIONS":
      return <Badge color="blue">{method}</Badge>
  }
  return <Badge>{method}</Badge>
}
