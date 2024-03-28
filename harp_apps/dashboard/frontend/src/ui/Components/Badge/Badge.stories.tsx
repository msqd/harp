import { Badge } from "./Badge"

export const Default = () => {
  const props = {
    className: "mx-1",
  }
  return (
    <>
      <Badge {...props}>Default (implicit)</Badge>
      <Badge {...props} color="default">
        Default (explicit)
      </Badge>
      <Badge {...props} color="green">
        Green
      </Badge>
      <Badge {...props} color="yellow">
        Yellow
      </Badge>
      <Badge {...props} color="orange">
        Orange
      </Badge>
      <Badge {...props} color="red">
        Red
      </Badge>
      <Badge {...props} color="blue">
        Blue
      </Badge>
      <Badge {...props} color="purple">
        Purple
      </Badge>
    </>
  )
}
