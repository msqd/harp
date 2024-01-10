import {Paginator as PaginatorComponent} from "./Paginator"
import {Pane} from "../Pane"
import {useState} from "react"

export const Paginator = () => {
    const [page, setPage] = useState(1)
    const props = {
        current: page,
        total: 273,
        setPage: (page: number) => setPage(page),
    }
    return (
        <Pane>
            <PaginatorComponent className="border-b" {...props} />
            <Pane hasDefaultBorder={false}>Hello, world.</Pane>
            <PaginatorComponent className="border-t" {...props} />
        </Pane>
    )
}
