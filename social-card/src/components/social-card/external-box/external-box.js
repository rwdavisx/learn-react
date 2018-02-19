import React, { Component } from 'react';
import './external-box.css';

class ExternalBox extends Component {
    constructor(props) {
        super(props);
        this.state = {
            title: this.props.input.title,
            text: this.props.input.text,
            image: this.props.input.image,
            link: this.props.input.link,
        }
    };

    render() {
        return (
            <div className={'container-fluid mb-1'}>
                <div className="row">
                    <div className='col-12'>
                        <img className="img-fluid w-100 rounded-top" src={this.state.image} alt='' />
                        <div className={'text-left border rounded-bottom p-2 bg-light'}>
                            <h6 className={'font-weight-bold m-0'}>{this.state.title}</h6>
                            <p className={'mb-1'}>{this.state.text}</p>
                            <p className={'font-weight-light m-0'}><a href={this.state.link}>{this.state.link}</a></p>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    handleComment(input) {
        console.log(input);
    };
};

export default ExternalBox;
