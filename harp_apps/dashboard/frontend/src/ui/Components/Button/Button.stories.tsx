import { Button } from './Button'

export const Default = () => (
  <>
    <Button variant="secondary">Secondary</Button>
    <Button variant="primary">Primary</Button>
  </>
)
export const Primary = () => <Button>Hello</Button>
export const Secondary = () => <Button variant="secondary">Hello</Button>
